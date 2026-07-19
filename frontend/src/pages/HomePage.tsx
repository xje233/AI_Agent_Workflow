import { useEffect } from 'react'
import NavBar from '@/components/NavBar'
import HistorySidebar from '@/components/HistorySidebar'
import ChatWindow from '@/components/ChatWindow'
import { useChatStore } from '@/stores/chat'

export default function HomePage() { const load = useChatStore((state) => state.loadConversations); useEffect(() => { void load() }, [load]); return <div className="page-container"><NavBar /><div className="home-body"><HistorySidebar /><ChatWindow /></div></div> }
