import axios from 'axios'
const client = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api', timeout: 2500 })
export const demoTickets = [
  { id:'TKT-2026-000249',subject:'Security incident #249',customer:'Customer 000072',channel:'Phone',priority:'CRITICAL',status:'IN_PROGRESS',agent:'Support Agent 004',due:'18 min' },
  { id:'TKT-2026-000247',subject:'Payment failure #247',customer:'Customer 000070',channel:'Live Chat',priority:'HIGH',status:'ASSIGNED',agent:'Support Agent 006',due:'1h 42m' },
  { id:'TKT-2026-000243',subject:'Login problem #243',customer:'Customer 000066',channel:'Email',priority:'MEDIUM',status:'IN_PROGRESS',agent:'Support Agent 008',due:'4h 08m' },
  { id:'TKT-2026-000241',subject:'Refund request #241',customer:'Customer 000064',channel:'Phone',priority:'MEDIUM',status:'RESOLVED',agent:'Support Agent 010',due:'Met' },
  { id:'TKT-2026-000238',subject:'Technical issue #238',customer:'Customer 000061',channel:'Live Chat',priority:'LOW',status:'ASSIGNED',agent:'Support Agent 002',due:'19h 20m' },
]
export const demoDashboard={source:'Verified starter dataset',metrics:{tickets:250,active:82,slaAtRisk:14,resolutionRate:67.2},channels:[{name:'Email',value:78},{name:'Live Chat',value:91},{name:'Phone',value:81}],trend:[{day:'Mon',created:31,resolved:22},{day:'Tue',created:38,resolved:27},{day:'Wed',created:44,resolved:32},{day:'Thu',created:33,resolved:30},{day:'Fri',created:46,resolved:35},{day:'Sat',created:29,resolved:24},{day:'Sun',created:29,resolved:20}],tickets:demoTickets}
export async function getDashboard(){try{const{data}=await client.get('/dashboard');return{...data,source:'Live API'}}catch{return demoDashboard}}
export async function getTickets(params={}){try{const{data}=await client.get('/tickets',{params});return data.items||data}catch{return demoTickets}}
export async function getTicket(ticketId){try{const{data}=await client.get(`/tickets/${ticketId}`);return data}catch{return {...(demoTickets.find(item=>item.id===ticketId)||demoTickets[0]),messages:[],events:[],routing:null}}}
export async function getTicketFormMeta(){const{data}=await client.get('/meta/ticket-form');return data}
export async function createTicket(payload){const{data}=await client.post('/tickets',payload);return data}
export async function updateTicket(ticketId,payload){const{data}=await client.patch(`/tickets/${ticketId}`,payload);return data}
export async function getAgents(){const{data}=await client.get('/agents');return data.items}
export async function getRoutingDecisions(){const{data}=await client.get('/routing/decisions');return data.items}
export async function getSlaItems(){const{data}=await client.get('/sla');return data}
export async function getAuditEvents(){const{data}=await client.get('/audit');return data.items}
export async function getValidation(){const{data}=await client.get('/validation');return data}
export async function getHealth(){const{data}=await client.get('/health',{baseURL:client.defaults.baseURL.replace(/\/api\/?$/,'')});return data}
export default client
