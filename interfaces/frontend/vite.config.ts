import path from 'node:path'
import os from 'node:os'
import { spawn } from 'node:child_process'
import { promises as fs } from 'node:fs'
import { randomUUID } from 'node:crypto'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, type Plugin } from 'vite'

const PROJECT_ROOT = path.resolve(import.meta.dirname, '..', '..')
const PYTHON = path.resolve(
  PROJECT_ROOT, '.venv', 'Scripts', 'python.exe',
)
const INGEST_CMD = [
  'from memory.vectorstore import ingest_file;',
  'import sys;',
  'print("OK", ingest_file(sys.argv[1], sys.argv[2]))',
].join(' ')
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024

function ragUploadPlugin(): Plugin {
  return {
    name: 'rag-upload',
    configureServer(server) {
      server.middlewares.use('/rag/upload', (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.end(JSON.stringify({ error: 'method not allowed' }))
          return
        }
        let rawName: string | undefined
        try {
          const h = req.headers['x-file-name']
          rawName = typeof h === 'string' ? decodeURIComponent(h) : undefined
        } catch {
          res.statusCode = 400
          res.end(JSON.stringify({ error: 'invalid file name header' }))
          return
        }
        if (!rawName) {
          res.statusCode = 400
          res.end(JSON.stringify({ error: 'missing x-file-name header' }))
          return
        }
        const { tmpName, chunks } = {
          tmpName: path.join(os.tmpdir(), `rag-upload-${randomUUID()}`),
          chunks: [] as Buffer[],
        }
        let size = 0
        req.on('data', (chunk: Buffer) => {
          size += chunk.length
          if (size > MAX_UPLOAD_BYTES) {
            res.statusCode = 413
            res.end(JSON.stringify({ error: 'file too large' }))
            req.destroy()
            return
          }
          chunks.push(chunk)
        })
        req.on('end', async () => {
          try {
            await fs.writeFile(tmpName, Buffer.concat(chunks))
            const name = rawName as string
            const python = spawn(PYTHON, ['-c', INGEST_CMD, tmpName, name], {
              cwd: PROJECT_ROOT,
              env: { ...process.env, PYTHONPATH: PROJECT_ROOT },
            })
            let stdout = ''
            let stderr = ''
            python.stdout.on('data', (d) => { stdout += d })
            python.stderr.on('data', (d) => { stderr += d })
            python.on('error', async (err) => {
              await fs.rm(tmpName, { force: true })
              res.statusCode = 500
              res.end(JSON.stringify({ error: `could not start ingest: ${err.message}` }))
            })
            python.on('close', async (code) => {
              await fs.rm(tmpName, { force: true })
              if (code === 0) {
                const source = stdout.trim().slice(3).trim() || rawName
                res.end(JSON.stringify({ ok: true, source }))
              } else {
                res.statusCode = 500
                res.end(JSON.stringify({ error: stderr.trim() || `ingest failed (exit ${code})` }))
              }
            })
          } catch (err) {
            await fs.rm(tmpName, { force: true })
            res.statusCode = 500
            res.end(JSON.stringify({ error: `upload failed: ${err}` }))
          }
        })
        req.on('error', async () => {
          await fs.rm(tmpName, { force: true })
        })
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), ragUploadPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})