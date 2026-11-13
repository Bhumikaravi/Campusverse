import { useNavigate } from "react-router-dom";
import DashboardUploadSection from "../components/DashboardUploadSection";

export default function Upload() {
  const navigate = useNavigate();

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <DashboardUploadSection onUploadSuccess={() => navigate("/my-uploads")} />
    </div>
  );
}
