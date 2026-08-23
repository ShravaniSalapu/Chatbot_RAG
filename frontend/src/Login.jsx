import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  loginUser,
} from "./api";
import { useAuth } from "./AuthContext";
import KnowaLogo from "./KnowaLogo";
import "./Login.css";

function Login() {

  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  async function handleSubmit(event) {

    event.preventDefault();

    setError("");

    if (!email.trim()) {

      setError(
        "Please enter your email."
      );

      return;
    }

    if (!password) {

      setError(
        "Please enter your password."
      );

      return;
    }

    try {

      setLoading(true);

      await login(
        email.trim(),
        password
      );

      /*
       * Login successful.
       * Go to dashboard.
       */

      navigate(
        "/dashboard",
        {
          replace: true,
        }
      );

    } catch (err) {

      console.error(
        "Login error:",
        err
      );

      setError(
        err.message ||
          "Unable to login."
      );

    } finally {

      setLoading(false);

    }
  }


  return (

    <div className="login-page">

      <div className="login-card">

        {/* Logo */}

        <div className="login-logo">
          <KnowaLogo />
        </div>


        {/* Heading */}

        <div className="login-heading">

          <h1>
            Welcome back
          </h1>

          <p>
            Sign in to your KNOWA AI
            dashboard
          </p>

        </div>


        {/* Error */}

        {error && (

          <div className="login-error">
            {error}
          </div>

        )}


        {/* Form */}

        <form
          onSubmit={handleSubmit}
          className="login-form"
        >

          <div className="form-group">

            <label htmlFor="email">
              Email
            </label>

            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value
                )
              }
              placeholder="you@example.com"
              autoComplete="email"
              disabled={loading}
            />

          </div>


          <div className="form-group">

            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={loading}
            />

          </div>


          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >

            {loading
              ? "Signing in..."
              : "Sign In"}

          </button>

        </form>


        <p className="login-footer" style={{ marginTop: "20px", fontSize: "13px" }}>
          Don't have an account?{" "}
          <a
            href="/signup"
            style={{ color: "#6d28d9", textDecoration: "none", fontWeight: "600" }}
          >
            Sign up
          </a>
        </p>

        <p className="login-footer">
          KNOWA AI · Intelligent
          document-powered chat
        </p>

      </div>

    </div>

  );
}

export default Login;