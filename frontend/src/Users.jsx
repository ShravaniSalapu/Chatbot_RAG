import { useEffect, useState } from "react";
import {
  getUsers,
  createUser,
  deleteUser,
} from "./api";

import "./App.css";


function Users() {
  const [users, setUsers] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create user modal
  const [showCreateModal, setShowCreateModal] =
    useState(false);

  const [creating, setCreating] =
    useState(false);

  const [newUserEmail, setNewUserEmail] =
    useState("");

  const [newUserName, setNewUserName] =
    useState("");

  const [newUserPassword, setNewUserPassword] =
    useState("");


  // ==========================================================
  // LOAD USERS
  // ==========================================================

  async function loadUsers() {
    try {
      setLoading(true);
      setError("");

      const data = await getUsers();

      setUsers(
        Array.isArray(data)
          ? data
          : []
      );

    } catch (err) {
      console.error(
        "Users loading error:",
        err
      );

      setError(
        err.message ||
        "Unable to load users."
      );

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadUsers();
  }, []);


  // ==========================================================
  // CREATE USER
  // ==========================================================

  async function handleCreateUser(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (
      !newUserEmail.trim() ||
      !newUserName.trim() ||
      !newUserPassword.trim()
    ) {
      setError(
        "Please fill in all fields."
      );
      return;
    }

    if (newUserPassword.length < 8) {
      setError(
        "Password must be at least 8 characters."
      );
      return;
    }

    try {
      setCreating(true);

      await createUser(
        newUserEmail.trim(),
        newUserName.trim(),
        newUserPassword
      );

      setSuccess(
        "User created successfully."
      );

      setNewUserEmail("");
      setNewUserName("");
      setNewUserPassword("");

      setShowCreateModal(false);

      await loadUsers();

      setTimeout(
        () => setSuccess(""),
        3000
      );

    } catch (err) {
      console.error(
        "Create user error:",
        err
      );

      setError(
        err.message ||
        "Unable to create user."
      );

    } finally {
      setCreating(false);
    }
  }


  // ==========================================================
  // DELETE USER
  // ==========================================================

  async function handleDeleteUser(
    userId,
    userEmail
  ) {
    if (
      userEmail.toLowerCase() ===
      "admin@gmail.com"
    ) {
      setError(
        "The main administrator cannot be deleted."
      );
      return;
    }

    const confirmed =
      window.confirm(
        `Are you sure you want to delete user "${userEmail}"?`
      );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setSuccess("");

      await deleteUser(userId);

      setSuccess(
        "User deleted successfully."
      );

      await loadUsers();

      setTimeout(
        () => setSuccess(""),
        3000
      );

    } catch (err) {
      console.error(
        "Delete user error:",
        err
      );

      setError(
        err.message ||
        "Unable to delete user."
      );
    }
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div>

      {/* HEADER */}

      <div className="topbar">

        <div>
          <h1>Users</h1>

          <p>
            All platform users and their usage
          </p>
        </div>

        <button
          className="create-button"
          onClick={() =>
            setShowCreateModal(true)
          }
        >
          + Add User
        </button>

      </div>


      {/* ERROR */}

      {error && (
        <div
          className="dashboard-error"
          style={{
            marginBottom: "20px",
          }}
        >
          {error}
        </div>
      )}


      {/* SUCCESS */}

      {success && (
        <div
          className="success-message"
          style={{
            marginBottom: "20px",
          }}
        >
          {success}
        </div>
      )}


      {/* USERS */}

      {loading ? (

        <div
          style={{
            textAlign: "center",
            padding: "40px",
          }}
        >
          <div className="loading-spinner"></div>
        </div>

      ) : (

        <div
          className="content-card"
          style={{
            marginTop: "20px",
          }}
        >

          <div className="card-header">

            <div>

              <h2>
                All Users
              </h2>

              <p>
                Every registered user on the platform
              </p>

            </div>

          </div>


          {users.length === 0 ? (

            <div className="empty-state">

              <div className="empty-icon">
                👥
              </div>

              <h3>
                No users found
              </h3>

            </div>

          ) : (

            <div
              style={{
                marginTop: "20px",
                overflowX: "auto",
              }}
            >

              {/* TABLE HEADER */}

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "2fr 2fr 100px 100px 120px 100px",
                  gap: "15px",
                  minWidth: "900px",
                  padding: "12px 15px",
                  background: "#f8fafc",
                  borderBottom:
                    "1px solid #e5e7eb",
                  fontSize: "12px",
                  fontWeight: "700",
                  color: "#64748b",
                  textTransform:
                    "uppercase",
                }}
              >

                <div>User</div>

                <div>Email</div>

                <div>Role</div>

                <div>Chats</div>

                <div>Documents</div>

                <div>Status</div>

              </div>


              {/* USERS */}

              {users.map((user) => (

                <div
                  key={user.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "2fr 2fr 100px 100px 120px 100px",
                    gap: "15px",
                    minWidth: "900px",
                    alignItems: "center",
                    padding: "15px",
                    borderBottom:
                      "1px solid #e5e7eb",
                  }}
                >

                  {/* USER */}

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >

                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        minWidth: "40px",
                        borderRadius: "50%",
                        background: "#ede9fe",
                        color: "#6d28d9",
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                          "center",
                        fontWeight: "700",
                      }}
                    >
                      {(
                        user.full_name ||
                        user.email ||
                        "U"
                      )
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <div
                      style={{
                        fontWeight: "600",
                        color: "#111827",
                      }}
                    >
                      {user.full_name ||
                        "Unknown"}
                    </div>

                  </div>


                  {/* EMAIL */}

                  <div
                    style={{
                      fontSize: "13px",
                      color: "#64748b",
                    }}
                  >
                    {user.email}
                  </div>


                  {/* ROLE */}

                  <div>

                    <span
                      style={{
                        padding:
                          "4px 10px",
                        borderRadius:
                          "20px",
                        fontSize: "11px",
                        fontWeight: "700",
                        textTransform:
                          "capitalize",
                        background:
                          user.role ===
                          "admin"
                            ? "#dcfce7"
                            : "#dbeafe",
                        color:
                          user.role ===
                          "admin"
                            ? "#15803d"
                            : "#1d4ed8",
                      }}
                    >
                      {user.role}
                    </span>

                  </div>


                  {/* CHATS */}

                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: "700",
                    }}
                  >
                    💬 {user.chat_count ?? 0}
                  </div>


                  {/* DOCUMENTS */}

                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: "700",
                    }}
                  >
                    📄 {user.document_count ?? 0}
                  </div>


                  {/* STATUS */}

                  <div>

                    <div
                      style={{
                        fontSize: "12px",
                        fontWeight: "600",
                        color:
                          user.is_active
                            ? "#15803d"
                            : "#dc2626",
                      }}
                    >
                      {user.is_active
                        ? "Active"
                        : "Disabled"}
                    </div>

                    {user.email
                      ?.toLowerCase() ===
                      "admin@gmail.com" && (
                      <div
                        style={{
                          marginTop: "4px",
                          fontSize: "10px",
                          color: "#6d28d9",
                          fontWeight: "700",
                        }}
                      >
                        MAIN ADMIN
                      </div>
                    )}

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>

      )}


      {/* ======================================================
          CREATE USER MODAL
      ====================================================== */}

      {showCreateModal && (

        <div
          className="modal-overlay"
          onClick={() =>
            setShowCreateModal(false)
          }
        >

          <div
            className="create-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>

                <h2>
                  Add New User
                </h2>

                <p>
                  New accounts are normal users.
                </p>

              </div>

              <button
                className="modal-close"
                onClick={() =>
                  setShowCreateModal(false)
                }
              >
                ×
              </button>

            </div>


            <form
              onSubmit={handleCreateUser}
            >

              <div className="form-group">

                <label>
                  Full Name
                </label>

                <input
                  type="text"
                  value={newUserName}
                  onChange={(event) =>
                    setNewUserName(
                      event.target.value
                    )
                  }
                  placeholder="Enter full name"
                  required
                />

              </div>


              <div className="form-group">

                <label>
                  Email
                </label>

                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(event) =>
                    setNewUserEmail(
                      event.target.value
                    )
                  }
                  placeholder="Enter email address"
                  required
                />

              </div>


              <div className="form-group">

                <label>
                  Password
                </label>

                <input
                  type="password"
                  value={newUserPassword}
                  onChange={(event) =>
                    setNewUserPassword(
                      event.target.value
                    )
                  }
                  placeholder="Minimum 8 characters"
                  required
                />

              </div>


              <div className="modal-actions">

                <button
                  type="button"
                  className="outline-button"
                  onClick={() =>
                    setShowCreateModal(false)
                  }
                  disabled={creating}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="create-button"
                  disabled={creating}
                >
                  {creating
                    ? "Creating..."
                    : "Create User"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}

export default Users;