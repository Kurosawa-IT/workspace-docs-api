import http from "k6/http";
import { check, group, sleep } from "k6";

export const options = {
  vus: Number(__ENV.VUS || 5),
  duration: __ENV.DURATION || "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE_URL = __ENV.BASE_URL;
const TOKEN = __ENV.TOKEN;
const WORKSPACE_ID = __ENV.WORKSPACE_ID;

const QUERY = __ENV.QUERY || "test";
const STATUS = __ENV.STATUS || "draft";
const TAG = __ENV.TAG || "export";

function requireEnv(name, value) {
  if (!value) {
    throw new Error(`missing env: ${name}`);
  }
}

export function setup() {
  requireEnv("BASE_URL", BASE_URL);
  requireEnv("TOKEN", TOKEN);
  requireEnv("WORKSPACE_ID", WORKSPACE_ID);

  return {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
  };
}

export default function (data) {
  const headers = data.headers;

  group("docs_list", function () {
    const res = http.get(
      `${BASE_URL}/workspaces/${WORKSPACE_ID}/docs?page=1&page_size=20&sort=updated_at_desc`,
      { headers }
    );
    check(res, {
      "docs_list_200": (r) => r.status === 200,
    });
  });

  group("docs_search", function () {
    const res = http.get(
      `${BASE_URL}/workspaces/${WORKSPACE_ID}/docs?page=1&page_size=20&sort=updated_at_desc&query=${encodeURIComponent(QUERY)}`,
      { headers }
    );
    check(res, {
      "docs_search_200": (r) => r.status === 200,
    });
  });

  group("docs_filter_status", function () {
    const res = http.get(
      `${BASE_URL}/workspaces/${WORKSPACE_ID}/docs?page=1&page_size=20&sort=updated_at_desc&status=${encodeURIComponent(STATUS)}`,
      { headers }
    );
    check(res, {
      "docs_filter_status_200": (r) => r.status === 200,
    });
  });

  group("docs_filter_tag", function () {
    const res = http.get(
      `${BASE_URL}/workspaces/${WORKSPACE_ID}/docs?page=1&page_size=20&sort=updated_at_desc&tag=${encodeURIComponent(TAG)}`,
      { headers }
    );
    check(res, {
      "docs_filter_tag_200": (r) => r.status === 200,
    });
  });

  sleep(1);
}