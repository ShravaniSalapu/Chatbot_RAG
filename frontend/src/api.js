const API_BASE_URL = "http://localhost:8000/api/v1";

/* =========================================================
   LOGIN
========================================================= */

export async function loginUser(email, password) {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",

    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },

    body: formData.toString(),
  });

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.detail ||
        "Login failed. Please check your email and password."
    );
  }

  /* Store access token */

  localStorage.setItem(
    "access_token",
    data.access_token
  );

  /* Store user information */

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
  return localStorage.getItem("access_token");
}


export function getStoredUser() {
  const user = localStorage.getItem("user");

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
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}


/* =========================================================
   COMMON AUTHENTICATED REQUEST
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

      ...(!isFormData && options.body
        ? {
            "Content-Type": "application/json",
          }
        : {}),

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

  /* Handle expired / invalid token */

  if (!response.ok) {
    if (response.status === 401) {
      logoutUser();

      throw new Error(
        "Your session has expired. Please log in again."
      );
    }

    throw new Error(
      data.detail ||
        `Request failed with status ${response.status}`
    );
  }

  return data;
}


/* =========================================================
   CHATBOTS
========================================================= */


/* ---------------------------------------------------------
   GET /api/v1/chatbots

   Get all chatbots for the logged-in tenant.
--------------------------------------------------------- */

export async function getChatbots() {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots`
  );
}


/* ---------------------------------------------------------
   GET /api/v1/chatbots/{chatbot_id}

   Get one chatbot.
--------------------------------------------------------- */

export async function getChatbot(chatbotId) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}`
  );
}


/* ---------------------------------------------------------
   POST /api/v1/chatbots

   Create a new chatbot.
--------------------------------------------------------- */

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


/* ---------------------------------------------------------
   PUT /api/v1/chatbots/{chatbot_id}

   Update an existing chatbot.
--------------------------------------------------------- */

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


/* ---------------------------------------------------------
   DELETE /api/v1/chatbots/{chatbot_id}

   Delete a chatbot.
--------------------------------------------------------- */

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


/* ---------------------------------------------------------
   GET /api/v1/chatbots/{chatbot_id}/settings

   Get chatbot appearance/settings.
--------------------------------------------------------- */

export async function getChatbotSettings(
  chatbotId
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/settings`
  );
}


/* ---------------------------------------------------------
   PUT /api/v1/chatbots/{chatbot_id}/settings

   Update chatbot appearance/settings.
--------------------------------------------------------- */

export async function updateChatbotSettings(
  chatbotId,
  settings
) {
  return authenticatedFetch(
    `${API_BASE_URL}/chatbots/${chatbotId}/settings`,
    {
      method: "PUT",

      body: JSON.stringify(settings),
    }
  );
}

/* =========================================================
   DOCUMENTS
========================================================= */

export async function getDocuments() {
  return authenticatedFetch(`${API_BASE_URL}/documents`);
}

/* =========================================================
   DOCUMENT UPLOAD
========================================================= */

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authenticatedFetch(
    `${API_BASE_URL}/upload`,
    {
      method: "POST",
      body: formData,
      headers: {
        Accept: "application/json",
      },
    }
  );

  return response;
}

export async function getUploadStatus(documentId) {
  return authenticatedFetch(
    `${API_BASE_URL}/upload/status/${documentId}`
  );
}

export async function deleteDocument(documentId) {
  return authenticatedFetch(
    `${API_BASE_URL}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );
}

export async function getChatbotDocuments(chatbotId) {
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
        document_id: documentId,
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
  return authenticatedFetch(`${API_BASE_URL}/tenants/me/usage`);
}

/* =========================================================
   API BASE URL
========================================================= */

export { API_BASE_URL };