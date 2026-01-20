const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type QueryParams = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: QueryParams) {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }
  return url.toString();
}

type ForwardOptions = {
  path: string;
  method?: string;
  token?: string;
  query?: QueryParams;
  body?: unknown;
  headers?: HeadersInit;
};

export async function forwardRequest(options: ForwardOptions) {
  const { path, method = "GET", token, query, body, headers } = options;
  const url = buildUrl(path, query);
  const init: RequestInit = {
    method,
    headers: {
      Accept: "application/json",
      ...headers,
    },
    cache: "no-store",
  };

  if (token) {
    (init.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  if (body !== undefined) {
    if (body instanceof FormData) {
      init.body = body;
    } else if (typeof body === "string") {
      init.body = body;
    } else {
      (init.headers as Record<string, string>)["Content-Type"] =
        "application/json";
      init.body = JSON.stringify(body);
    }
  }

  try {
    return await fetch(url, init);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unable to reach backend.";
    return new Response(
      JSON.stringify({
        error: { code: "BACKEND_UNREACHABLE", message },
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

export async function proxyJsonResponse(res: Response) {
  const text = await res.text();
  const headers = new Headers();
  headers.set("Content-Type", res.headers.get("content-type") || "application/json");
  return new Response(text, { status: res.status, headers });
}

export function proxyStreamResponse(res: Response) {
  const headers = new Headers();
  const contentType = res.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  const disposition = res.headers.get("content-disposition");
  if (disposition) {
    headers.set("Content-Disposition", disposition);
  }
  return new Response(res.body, { status: res.status, headers });
}
