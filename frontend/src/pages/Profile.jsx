import { useState } from "react";
import { User, Mail, GraduationCap, Building2, Calendar, ShieldCheck, Edit3, Check } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function Profile() {
  const { user } = useAuth();
  const { showToast } = useToast();

  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState({
    name: user?.name || "Bhumika Ravi",
    email: user?.email || "bhumika@college.edu",
    department: user?.department || "Computer Science & Engineering",
    semester: user?.semester || "4",
    college: "Campus University of Technology",
    bio: "Passionate Computer Science student. Contributing semester notes, algorithm guides, and past exam solutions for peers.",
  });

  const handleSave = (e) => {
    e.preventDefault();
    setIsEditing(false);
    showToast("Profile details updated successfully!", "success");
    // Update local storage
    const stored = JSON.parse(localStorage.getItem("cv-user") || "{}");
    localStorage.setItem("cv-user", JSON.stringify({ ...stored, ...profile }));
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="card overflow-hidden bg-white border border-gray-200">
        {/* Banner */}
        <div className="h-36 bg-gray-100 border-b border-gray-200 p-6 sm:h-44" />

        <div className="relative px-6 pb-8">
          {/* Avatar and basic info */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="-mt-16 flex items-end gap-4 sm:-mt-20">
              <div className="flex h-24 w-24 items-center justify-center rounded-2xl border-4 border-white bg-gray-200 text-3xl font-bold text-gray-800 shadow-sm sm:h-28 sm:w-28">
                {profile.name[0]?.toUpperCase() || "U"}
              </div>
              <div className="mb-2">
                <div className="flex items-center gap-2">
                  <h1 className="font-display text-2xl font-bold text-gray-900">{profile.name}</h1>
                  {user?.role === "admin" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 border border-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-800">
                      <ShieldCheck size={12} /> Admin
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500">{profile.email}</p>
              </div>
            </div>

            <button
              onClick={() => setIsEditing((prev) => !prev)}
              className="btn-secondary self-start sm:self-auto"
            >
              {isEditing ? (
                <>
                  <Check size={16} /> Cancel Editing
                </>
              ) : (
                <>
                  <Edit3 size={16} /> Edit Profile
                </>
              )}
            </button>
          </div>

          {/* Profile Form / View */}
          {isEditing ? (
            <form onSubmit={handleSave} className="mt-8 space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    className="input-field"
                    required
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={profile.email}
                    disabled
                    className="input-field cursor-not-allowed opacity-60"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Department
                  </label>
                  <input
                    type="text"
                    value={profile.department}
                    onChange={(e) => setProfile({ ...profile, department: e.target.value })}
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Semester
                  </label>
                  <select
                    value={profile.semester}
                    onChange={(e) => setProfile({ ...profile, semester: e.target.value })}
                    className="input-field"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>
                        Semester {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Institution / University
                  </label>
                  <input
                    type="text"
                    value={profile.college}
                    onChange={(e) => setProfile({ ...profile, college: e.target.value })}
                    className="input-field"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    About / Bio
                  </label>
                  <textarea
                    rows={3}
                    value={profile.bio}
                    onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                    className="input-field resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-3">
                <button type="submit" className="btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          ) : (
            <div className="mt-8 space-y-6">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
                  About
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-700">
                  {profile.bio}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex items-center gap-3 rounded-lg border border-gray-200 p-3.5 bg-white">
                  <Building2 size={20} className="text-gray-700" />
                  <div>
                    <p className="text-xs text-gray-400">Department</p>
                    <p className="text-sm font-semibold text-gray-900">{profile.department}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 rounded-lg border border-gray-200 p-3.5 bg-white">
                  <GraduationCap size={20} className="text-gray-700" />
                  <div>
                    <p className="text-xs text-gray-400">Current Level</p>
                    <p className="text-sm font-semibold text-gray-900">Semester {profile.semester}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 rounded-lg border border-gray-200 p-3.5 bg-white">
                  <Mail size={20} className="text-gray-700" />
                  <div>
                    <p className="text-xs text-gray-400">College Email</p>
                    <p className="text-sm font-semibold text-gray-900">{profile.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 rounded-lg border border-gray-200 p-3.5 bg-white">
                  <Calendar size={20} className="text-gray-700" />
                  <div>
                    <p className="text-xs text-gray-400">Member Since</p>
                    <p className="text-sm font-semibold text-gray-900">August 2026</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
