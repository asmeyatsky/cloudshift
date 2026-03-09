import SettingsPanel from "../components/config/SettingsPanel";

export default function SettingsPage() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="mt-1 text-base text-gray-500">
          Configure project settings and migration parameters
        </p>
      </div>
      <SettingsPanel />
    </div>
  );
}
