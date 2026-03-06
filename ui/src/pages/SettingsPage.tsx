import SettingsPanel from "../components/config/SettingsPanel";

export default function SettingsPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure project settings and migration parameters
        </p>
      </div>
      <SettingsPanel />
    </div>
  );
}
