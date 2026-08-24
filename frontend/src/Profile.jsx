import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { updateUserProfile, changeUserPassword } from "./api";
import "./App.css";

function Profile() {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Profile form state
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");

  // Password change form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setEmail(user.email || "");
    }
  }, [user]);

  async function handleProfileUpdate(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }

    if (!email.trim()) {
      setError("Please enter your email.");
      return;
    }

    try {
      setLoading(true);
      await updateUserProfile(fullName.trim(), email.trim());
      await refreshUser();
      setSuccess("Profile updated successfully!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Profile update error:", err);
      setError(err.message || "Unable to update profile.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordChange(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!currentPassword) {
      setError("Please enter your current password.");
      return;
    }

    if (!newPassword) {
      setError("Please enter a new password.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);
      await changeUserPassword(currentPassword, newPassword);
      setSuccess("Password changed successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      console.error("Password change error:", err);
      setError(err.message || "Unable to change password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="topbar">
        <div>
          <h1>Profile Settings</h1>
          <p>Manage your account information and security</p>
        </div>
      </div>

      {error && (
        <div className="dashboard-error" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {success && (
        <div className="success-message" style={{ marginBottom: "20px" }}>
          {success}
        </div>
      )}

      <div className="content-grid">
        <div className="content-card">
          <div className="card-header">
            <div>
              <h2>Profile Information</h2>
              <p>Update your personal details</p>
            </div>
          </div>

          <form onSubmit={handleProfileUpdate} style={{ marginTop: "20px" }}>
            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={loading}
                placeholder="Enter your full name"
              />
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                placeholder="Enter your email"
              />
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Role</label>
              <input
                type="text"
                value={user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "User"}
                disabled
                style={{ background: "#f8fafc" }}
              />
            </div>

            <button
              type="submit"
              className="create-button"
              disabled={loading}
            >
              {loading ? "Updating..." : "Update Profile"}
            </button>
          </form>
        </div>

        <div className="content-card">
          <div className="card-header">
            <div>
              <h2>Change Password</h2>
              <p>Update your password for security</p>
            </div>
          </div>

          <form onSubmit={handlePasswordChange} style={{ marginTop: "20px" }}>
            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={loading}
                placeholder="Enter current password"
              />
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={loading}
                placeholder="Enter new password (min 8 characters)"
              />
            </div>

            <div className="form-group" style={{ marginBottom: "15px" }}>
              <label>Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={loading}
                placeholder="Confirm new password"
              />
            </div>

            <button
              type="submit"
              className="create-button"
              disabled={loading}
            >
              {loading ? "Changing..." : "Change Password"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Profile;