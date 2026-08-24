const API_BASE_URL = "http://localhost:8000/api/v1";

/* =========================================================
   ERROR HELPER
========================================================= */

function getErrorMessage(data, fallback) {
  if (!data || !data.detail) {
    return fallback;
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((error) => {
        if (typeof error === "string") {
          return error;
        }

        return error?.msg || JSON.stringify(error);
      })
      .join(", ");
  }

  if (typeof data.detail === "object") {
    return JSON.stringify(data.detail);
  }

  return fallback;
}


/* =========================================================
   AUTHENTICATED REQUEST
========================================================= */

async function authenticatedFetch(url, options = {}) {
  const token = getAccessToken();

  if (!token) {
    throw new Error(
      "Authentication token not found. Please log in again."
    );
  }

  const isFormData = options.body instanceof FormData;

  const response = await fetch(url, {
    ...options,

    headers: {
      Accept: "application/json",

      ...(
        !isFormData && options.body
          ? {
              "Content-Type": "application/json",
            }
          : {}
      ),

      ...(options.headers || {}),

      Authorization: `Bearer ${token}`,
    },
  });

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    if (response.status === 401) {
      logoutUser();

      throw new Error(
        "Your session has expired. Please log in again."
      );
    }

    if (response.status === 403) {
      throw new Error(
        getErrorMessage(
          data,
          "You don't have permission to access this resource."
        )
      );
    }

    if (response.status === 404) {
      throw new Error(
        getErrorMessage(
          data,
          "Resource not found."
        )
      );
    }

    if (response.status === 422) {
      throw new Error(
        getErrorMessage(
          data,
          "Invalid request data."
        )
      );
    }

    throw new Error(
      getErrorMessage(
        data,
        `Request failed with status ${response.status}`
      )
    );
  }

  return data;
}


/* =========================================================
   REGISTER
========================================================= */

export async function registerUser(
  tenantName,
  fullName,
  email,
  password
) {
  const payload = {
    tenant_name: tenantName,
    full_name: fullName,
    email,
    password,
  };

  const response = await fetch(
    `${API_BASE_URL}/auth/register`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },

      body: JSON.stringify(payload),
    }
  );

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Registration failed. Please try again."
      )
    );
  }

  return data;
}


/* =========================================================
   LOGIN
========================================================= */

export async function loginUser(
  email,
  password
) {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded",

        Accept: "application/json",
      },

      body: formData.toString(),
    }
  );

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Login failed. Please check your email and password."
      )
    );
  }

  /* Store token */

  localStorage.setItem(
    "access_token",
    data.access_token
  );

  /* Store basic user information */

  localStorage.setItem(
    "user",
    JSON.stringify({
      user_id: data.user_id,
      tenant_id: data.tenant_id,
      email: data.email,
      role: data.role,
    })
  );

  return data;
}


/* =========================================================
   AUTH HELPERS
========================================================= */

export function getAccessToken() {
  return localStorage.getItem(
    "access_token"
  );
}


export function getStoredUser() {
  const user = localStorage.getItem(
    "user"
  );

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}


export function logoutUser() {
  localStorage.removeItem(
    "access_token"
  );

  localStorage.removeItem(
    "user"
  );
}


export async function getCurrentUser() {
  const token = getAccessToken();

  if (!token) {
    throw new Error(
      "No authentication token found"
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      method: "GET",

      headers: {
        Accept: "application/json",

        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    if (response.status === 401) {
      logoutUser();

      throw new Error(
        "Your session has expired. Please log in again."
      );
    }

    throw new Error(
      getErrorMessage(
        data,
        `Request failed with status ${response.status}`
      )
    );
  }

  return data;
}


/* =========================================================
   ADMIN API
========================================================= */

/*
 * IMPORTANT:
 * These endpoints are protected by the backend.
 *
 * Only admin@gmail.com / admin role
 * can access admin-only endpoints.
 */


export async function getAdminStats() {
  return authenticatedFetch(
    `${API_BASE_URL}/admin/stats`
  );
}


export async function getUsers() {
  return authenticatedFetch(
    `${API_BASE_URL}/admin/users`
  );
}


export async function getRecentActivity() {
  return authenticatedFetch(
    `${API_BASE_URL}/admin/recent-activity`
  );
}


export async function getAnalytics() {
  return authenticatedFetch(
    `${API_BASE_URL}/analytics`
  );
}


export async function getAdminUsage() {
  return authenticatedFetch(
    `${API_BASE_URL}/admin/usage`
  );
}


/* =========================================================
   USER PROFILE
========================================================= */

export async function updateUserProfile(
  fullName,
  email
) {
  return authenticatedFetch(
    `${API_BASE_URL}/users/me`,
    {
      method: "PUT",

      body: JSON.stringify({
        full_name: fullName,
        email,
      }),
    }
  );
}


export async function changeUserPassword(
  currentPassword,
  newPassword
) {
  return authenticatedFetch(
    `${API_BASE_URL}/users/me/password`,
    {
      method: "PUT",

      body: JSON.stringify({
        current_password:
          currentPassword,

        new_password:
          newPassword,
      }),
    }
  );
}


/* =========================================================
   CREATE USER
========================================================= */

/*
 * IMPORTANT:
 *
 * The backend creates every user as role="user".
 *
 * There is intentionally NO role parameter.
 */

export async function createUser(
  email,
  fullName,
  password
) {
  return authenticatedFetch(
    `${API_BASE_URL}/users/create`,
    {
      method: "POST",

      body: JSON.stringify({
        email,
        full_name: fullName,
        password,
      }),
    }
  );
}


/* =========================================================
   DELETE USER
========================================================= */

export async function deleteUser(
  userId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/users/${userId}`,
    {
      method: "DELETE",
    }
  );
}


/* =========================================================
   CHATBOTS
========================================================= */

export async function getChatbots() {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots`
  );
}


export async function getChatbot(
  chatbotId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}`
  );
}


export async function createChatbot(
  name,
  description
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots`,
    {
      method: "POST",

      body: JSON.stringify({
        name,
        description,
      }),
    }
  );
}


export async function updateChatbot(
  chatbotId,
  name,
  description,
  status
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}`,
    {
      method: "PUT",

      body: JSON.stringify({
        name,
        description,
        status,
      }),
    }
  );
}


export async function deleteChatbot(
  chatbotId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}`,
    {
      method: "DELETE",
    }
  );
}


/* =========================================================
   CHATBOT SETTINGS
========================================================= */

export async function getChatbotSettings(
  chatbotId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/settings`
  );
}


export async function updateChatbotSettings(
  chatbotId,
  settings
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/settings`,
    {
      method: "PUT",

      body: JSON.stringify(
        settings
      ),
    }
  );
}


/* =========================================================
   DOCUMENTS
========================================================= */

export async function getDocuments() {
  return authenticatedFetch(
    `${API_BASE_URL}/documents`
  );
}


/* =========================================================
   DOCUMENT UPLOAD
========================================================= */

export async function uploadDocument(
  file
) {
  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  return authenticatedFetch(
    `${API_BASE_URL}/upload`,
    {
      method: "POST",

      body: formData,
    }
  );
}


export async function getUploadStatus(
  documentId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/upload/status/${documentId}`
  );
}


export async function deleteDocument(
  documentId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );
}


/* =========================================================
   CHATBOT DOCUMENTS
========================================================= */

export async function getChatbotDocuments(
  chatbotId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/documents`
  );
}


export async function attachDocument(
  chatbotId,
  documentId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/documents`,
    {
      method: "POST",

      body: JSON.stringify({
        document_id:
          documentId,
      }),
    }
  );
}


export async function detachDocument(
  chatbotId,
  documentId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );
}


/* =========================================================
   USAGE
========================================================= */

export async function getUsage() {
  return authenticatedFetch(
    `${API_BASE_URL}/tenants/me/usage`
  );
}


/*
 * DO NOT ADD getAdminUsage() HERE.
 *
 * It already exists in the ADMIN API section above.
 */


/* =========================================================
   AUDIT LOGS
========================================================= */

export async function getAuditLogs(
  action = null,
  limit = 50,
  offset = 0
) {
  const params =
    new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

  if (action) {
    params.append(
      "action",
      action
    );
  }

  return authenticatedFetch(
    `${API_BASE_URL}/audit-logs?${params.toString()}`
  );
}


/* =========================================================
   API BASE URL
========================================================= */

export {
  API_BASE_URL
};



