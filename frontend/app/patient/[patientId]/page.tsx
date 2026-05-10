import PatientDashboard from "./PatientDashboard";

export default function PatientPage({ params }: { params: { patientId: string } }) {
  return <PatientDashboard patientId={params.patientId} />;
}
