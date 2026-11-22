import { TooltipProvider } from "@/components/ui/tooltip";
import ChatPage from "@/pages/ChatPage";

export default function App() {
  return (
    <TooltipProvider>
      <ChatPage />
    </TooltipProvider>
  );
}