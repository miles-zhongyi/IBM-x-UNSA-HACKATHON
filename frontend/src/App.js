import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import Landing from "@/pages/Landing";
import PortalLayout from "@/components/layout/PortalLayout";

import DoctorDashboard from "@/pages/doctor/Dashboard";
import DoctorPatients from "@/pages/doctor/Patients";
import DoctorPatientProfile from "@/pages/doctor/PatientProfile";
import DoctorUpload from "@/pages/doctor/Upload";
import DoctorQueries from "@/pages/doctor/Queries";
import DoctorSettings from "@/pages/doctor/Settings";

import PatientDashboard from "@/pages/patient/Dashboard";
import PatientAIAssistant from "@/pages/patient/AIAssistant";
import PatientRecords from "@/pages/patient/Records";
import PatientAskDoctor from "@/pages/patient/AskDoctor";
import PatientSettings from "@/pages/patient/Settings";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Toaster position="top-right" richColors />
        <Routes>
          <Route path="/" element={<Landing />} />

          <Route path="/doctor" element={<PortalLayout role="doctor" />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DoctorDashboard />} />
            <Route path="patients" element={<DoctorPatients />} />
            <Route path="patients/:id" element={<DoctorPatientProfile />} />
            <Route path="upload" element={<DoctorUpload />} />
            <Route path="queries" element={<DoctorQueries />} />
            <Route path="settings" element={<DoctorSettings />} />
          </Route>

          <Route path="/patient" element={<PortalLayout role="patient" />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<PatientDashboard />} />
            <Route path="ai-assistant" element={<PatientAIAssistant />} />
            <Route path="records" element={<PatientRecords />} />
            <Route path="ask-doctor" element={<PatientAskDoctor />} />
            <Route path="settings" element={<PatientSettings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
