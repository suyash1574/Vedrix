import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import InterviewRoom from './pages/InterviewRoom';
import CandidateApplicationForm from './pages/CandidateApplicationForm';
import AssessmentRoom from './pages/AssessmentRoom';
import AdminDashboard from './pages/AdminDashboard';
import HRDashboard from './pages/HRDashboard';
import StudentDashboard from './pages/StudentDashboard';
import InterviewReport from './pages/InterviewReport';
import InterviewReplay from './pages/InterviewReplay';
import SkillGapAnalysis from './pages/SkillGapAnalysis';
import TeamAnalytics from './pages/TeamAnalytics';
import CertificateVerification from './pages/CertificateVerification';
import SystemHealth from './pages/SystemHealth';
import AuditLogs from './pages/AuditLogs';
import SystemConfig from './pages/SystemConfig';
import CandidatePipeline from './pages/CandidatePipeline';
import FeedbackSurvey from './pages/FeedbackSurvey';
import HRFeedback from './pages/HRFeedback';
import Schedule from './pages/Schedule';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import DataProcessingAgreement from './pages/DataProcessingAgreement';
import AccessibilityStatement from './pages/AccessibilityStatement';
import SettingsPage from './pages/SettingsPage';
import LandingPage from './pages/LandingPage';
import SupervisorDashboard from './pages/SupervisorDashboard';
import CandidateProfilePage from './pages/CandidateProfilePage';
import ProfilePage from './pages/ProfilePage';
import CoachingPlanPage from './pages/CoachingPlanPage';
import HRMatchingDashboard from './pages/HRMatchingDashboard';
import WorkflowKanban from './pages/WorkflowKanban';
import HiringWorkflow from './pages/HiringWorkflow';
import ViolationMonitor from './pages/ViolationMonitor';
import ObservabilityPanel from './pages/ObservabilityPanel';
import QAQualityWidget from './pages/QAQualityWidget';
import SentimentTimeline from './pages/SentimentTimeline';
import EnrichmentSummary from './pages/EnrichmentSummary';
import NotFound from './pages/NotFound';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import CookieConsent from './components/CookieConsent';
import ProtectedRoute from './components/ProtectedRoute';
import CommandPalette from './components/CommandPalette';
import Toast from './components/Toast';
import AIAssistant from './components/AIAssistant';
import AgentActivityPanel from './components/AgentActivityPanel';
import PageTransition from './components/PageTransition';
import ErrorBoundary from './components/ErrorBoundary';
import useAuthStore from './store/useAuthStore';

function App() {
  const { checkAuth, isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Helper to get dashboard path based on user type
  const getDashboardPath = (user) => {
    if (user?.user_type === 'admin') return '/admin';
    if (user?.user_type === 'hr') return '/hr';
    return '/dashboard'; // student default
  };

  // Determine if we should show the navbar/footer
  const isInterviewRoom = location.pathname === '/interview';
  const isReport = location.pathname.startsWith('/report');
  const isVerify = location.pathname.startsWith('/verify');
  const isReplay = location.pathname.startsWith('/replay');
  const isSkillGap = location.pathname.startsWith('/skill-gap');
  const isTeamAnalytics = location.pathname.startsWith('/analytics/team');
  const isLegalPage = ['/privacy', '/terms', '/dpa', '/accessibility'].includes(location.pathname);
  const showNavbar = !isInterviewRoom && !isReport && !isVerify && !isReplay && !isSkillGap && !isTeamAnalytics && !isLegalPage;
  const showFooter = !isInterviewRoom && !isReport && !isVerify;

  // Show the agent activity panel only on admin/HR-facing routes
  const isAdminOrHRRoute =
    isAuthenticated &&
    (user?.user_type === 'admin' || user?.user_type === 'hr') &&
    (location.pathname.startsWith('/admin') || location.pathname.startsWith('/hr')) &&
    !isInterviewRoom;

  return (
    <div className="app-shell bg-[#020617] text-white">
      {/* Skip to main content link for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {showNavbar && <Navbar />}

      <main
        id="main-content"
        className={`app-main ${showNavbar ? 'app-main--with-navbar' : ''}`}
      >
        <ErrorBoundary>
        <PageTransition>
          <Routes location={location} key={location.pathname}>
            {/* Public Routes */}
            <Route path="/home" element={<LandingPage />} />
            <Route path="/" element={
              isAuthenticated ? <Navigate to={getDashboardPath(user)} replace /> : <LandingPage />
            } />

            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Public recruiter-configured candidate application */}
            <Route path="/apply/:token" element={<CandidateApplicationForm />} />
            <Route path="/assessment/:assignmentId" element={<AssessmentRoom />} />

            {/* Interview Room (Public-ish/Self-protected) */}
            <Route path="/interview" element={<InterviewRoom />} />

            {/* Protected Student Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentDashboard />
              </ProtectedRoute>
            } />

            {/* Protected HR Routes */}
            <Route path="/hr" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <HRDashboard />
              </ProtectedRoute>
            } />

            {/* Protected Admin Routes */}
            <Route path="/admin" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            } />

            {/* Protected Report Route */}
            <Route path="/report/:sessionId" element={
              <ProtectedRoute>
                <InterviewReport />
              </ProtectedRoute>
            } />

            {/* Protected Replay Route */}
            <Route path="/replay/:sessionId" element={
              <ProtectedRoute>
                <InterviewReplay />
              </ProtectedRoute>
            } />

            {/* Protected Skill Gap Analysis Route */}
            <Route path="/skill-gap/:sessionId" element={
              <ProtectedRoute>
                <SkillGapAnalysis />
              </ProtectedRoute>
            } />

            {/* Protected Team Analytics Route (Admin only) */}
            <Route path="/analytics/team" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <TeamAnalytics />
              </ProtectedRoute>
            } />

            {/* Public Certificate Verification Route */}
            <Route path="/verify/:token" element={<CertificateVerification />} />

            {/* Protected System Health Route (Admin only) */}
            <Route path="/admin/health" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <SystemHealth />
              </ProtectedRoute>
            } />

            {/* Protected Audit Logs Route (Admin only) */}
            <Route path="/admin/audit-logs" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AuditLogs />
              </ProtectedRoute>
            } />

            {/* Protected System Config Route (Admin only) */}
            <Route path="/admin/config" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <SystemConfig />
              </ProtectedRoute>
            } />

            {/* Protected AI Supervisor Route (Admin only) */}
            <Route path="/admin/supervisor" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <SupervisorDashboard />
              </ProtectedRoute>
            } />

            {/* Protected Candidate Pipeline Route (HR/Admin) */}
            <Route path="/hr/pipeline" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <CandidatePipeline />
              </ProtectedRoute>
            } />

            {/* Public Feedback Survey Route */}
            <Route path="/feedback/survey" element={<FeedbackSurvey />} />

            {/* Protected HR Feedback Route */}
            <Route path="/hr/feedback/:sessionId" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <HRFeedback />
              </ProtectedRoute>
            } />

            {/* Protected Schedule Route (HR/Admin) */}
            <Route path="/hr/schedule" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <Schedule />
              </ProtectedRoute>
            } />

            {/* Protected Settings Route */}
            <Route path="/settings" element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            } />

            {/* Dedicated Profile Route (all authenticated roles) */}
            <Route path="/profile" element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            } />

            {/* ── Agentic Platform Routes ─────────────────────────────── */}

            {/* Candidate Skill Profile (Student) */}
            <Route path="/dashboard/profile" element={
              <ProtectedRoute allowedRoles={['student']}>
                <CandidateProfilePage />
              </ProtectedRoute>
            } />

            {/* Coaching Plan (Student) */}
            <Route path="/dashboard/coaching/:planId" element={
              <ProtectedRoute allowedRoles={['student']}>
                <CoachingPlanPage />
              </ProtectedRoute>
            } />

            {/* HR Matching Dashboard */}
            <Route path="/hr/drives/:driveId/rankings" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <HRMatchingDashboard />
              </ProtectedRoute>
            } />

            {/* End-to-end recruiter hiring workflow */}
            <Route path="/hr/drives/:driveId/hiring-workflow" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <HiringWorkflow />
              </ProtectedRoute>
            } />

            {/* Workflow Kanban Pipeline */}
            <Route path="/hr/drives/:driveId/pipeline" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <WorkflowKanban />
              </ProtectedRoute>
            } />

            {/* Violation Monitor / Proctor */}
            <Route path="/hr/interviews/:sessionId/proctor" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <ViolationMonitor />
              </ProtectedRoute>
            } />

            {/* Sentiment Timeline */}
            <Route path="/hr/interviews/:sessionId/sentiment" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <SentimentTimeline />
              </ProtectedRoute>
            } />

            {/* Enrichment Summary */}
            <Route path="/hr/candidates/:candidateId/enrichment" element={
              <ProtectedRoute allowedRoles={['hr', 'admin']}>
                <EnrichmentSummary />
              </ProtectedRoute>
            } />

            {/* Admin Audit Trail / Observability */}
            <Route path="/admin/audit-trail" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <ObservabilityPanel />
              </ProtectedRoute>
            } />

            {/* Admin QA Monitor */}
            <Route path="/admin/qa-monitor" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <QAQualityWidget />
              </ProtectedRoute>
            } />

            {/* Public Legal Pages */}
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/dpa" element={<DataProcessingAgreement />} />
            <Route path="/accessibility" element={<AccessibilityStatement />} />

            {/* 404 */}
            <Route path="/404" element={<NotFound />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </PageTransition>
        </ErrorBoundary>
      </main>

      {showFooter && <Footer />}
      <CookieConsent />

      {/* Global UI: command palette, toasts */}
      <CommandPalette />
      <Toast />

      {/* Authenticated-only floating UI */}
      {isAuthenticated && <AIAssistant />}
      {isAdminOrHRRoute && <AgentActivityPanel />}
    </div>
  );
}

export default App;
