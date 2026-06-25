import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, FileText, Users, GitCompare, Upload,
  ShieldAlert, Search, Activity, ChevronRight
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Quotations from './pages/Quotations';
import QuotationDetail from './pages/QuotationDetail';
import Suppliers from './pages/Suppliers';
import SupplierDetail from './pages/SupplierDetail';
import Compare from './pages/Compare';
import UploadPage from './pages/UploadPage';
import Intelligence from './pages/Intelligence';
import SearchPage from './pages/SearchPage';
import Observability from './pages/Observability';

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">N</div>
          <div>
            <div className="logo-text">NexuSolve</div>
            <div className="logo-sub">CRM Intelligence</div>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="nav-section-label">Overview</div>
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard /> Dashboard
        </NavLink>

        <div className="nav-section-label">Data</div>
        <NavLink to="/quotations" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <FileText /> Quotations
        </NavLink>
        <NavLink to="/suppliers" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Users /> Suppliers
        </NavLink>
        <NavLink to="/compare" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <GitCompare /> Compare
        </NavLink>

        <div className="nav-section-label">Intelligence</div>
        <NavLink to="/intelligence" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <ShieldAlert /> Risk Analysis
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Search /> AI Search
        </NavLink>

        <div className="nav-section-label">System</div>
        <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Upload /> Upload
        </NavLink>
        <NavLink to="/observability" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <Activity /> Observability
        </NavLink>
      </nav>
    </aside>
  );
}

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/quotations" element={<Quotations />} />
          <Route path="/quotations/:id" element={<QuotationDetail />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/suppliers/:id" element={<SupplierDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/intelligence" element={<Intelligence />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/observability" element={<Observability />} />
        </Routes>
      </main>
    </div>
  );
}
