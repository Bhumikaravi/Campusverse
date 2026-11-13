import { Construction } from "lucide-react";
import { EmptyState } from "../components/EmptyState";

export default function ComingSoon({ title }) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <EmptyState
        icon={Construction}
        title={`${title} — coming next`}
        message="This page's layout and API wiring will be built in the next pass, same as every other page here."
      />
    </div>
  );
}
