import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { DocumentsWindow } from './features/documents/DocumentsWindow'
import './styles.css'

const Root = window.location.hash === '#/documents' ? DocumentsWindow : App

createRoot(document.getElementById('root')!).render(<StrictMode><Root /></StrictMode>)
