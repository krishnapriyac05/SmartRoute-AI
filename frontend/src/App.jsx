import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import TicketDetails from './pages/TicketDetails'
import Agents from './pages/Agents'
import Routing from './pages/Routing'
import SLAMonitor from './pages/SLAMonitor'
import Analytics from './pages/Analytics'
import DataGenerator from './pages/DataGenerator'
import Validation from './pages/Validation'
import AuditTrail from './pages/AuditTrail'
import './styles/global.css'
import './styles/layout.css'
import './styles/dashboard.css'
import './styles/secondary.css'
import './styles/forms.css'

export default function App() {
  return <BrowserRouter><div className="app-shell"><Sidebar /><div className="app-main"><Navbar /><main className="page-content"><Routes>
    <Route path="/" element={<Dashboard />} /><Route path="/tickets" element={<Tickets />} /><Route path="/tickets/:ticketId" element={<TicketDetails />} />
    <Route path="/agents" element={<Agents />} /><Route path="/routing" element={<Routing />} /><Route path="/sla" element={<SLAMonitor />} />
    <Route path="/analytics" element={<Analytics />} /><Route path="/generator" element={<DataGenerator />} /><Route path="/validation" element={<Validation />} /><Route path="/audit" element={<AuditTrail />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></main></div></div></BrowserRouter>
}
