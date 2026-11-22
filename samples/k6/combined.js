import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    signup: {
      executor: 'ramping-vus',
      exec: 'signupScenario',
      stages: [
        { duration: '30s', target: 10 },
        { duration: '60s', target: 10 },
        { duration: '15s', target: 0 },
      ],
    },
    login: {
      executor: 'constant-vus',
      exec: 'loginScenario',
      vus: 5,
      duration: '90s',
    },
    token: {
      executor: 'shared-iterations',
      exec: 'tokenScenario',
      vus: 2,
      iterations: 20,
    },
  },
  thresholds: {
    'http_req_duration{endpoint:register}': ['p(95)<800'],
    'http_req_duration{endpoint:login}': ['p(95)<=500'],
    'http_req_failed{endpoint:login}': ['rate<=0.01'],
    'http_req_duration{endpoint:token}': ['avg<300'],
  },
};

function warmUp() {
  http.get('http://127.0.0.1:8765/health', { tags: { endpoint: 'health' } });
}

function tokenFlow(user) {
  http.post('http://127.0.0.1:8765/token', JSON.stringify({ user: user }), { tags: { endpoint: 'token' } });
}

export function signupScenario() {
  warmUp();
  const res = http.post('http://127.0.0.1:8765/register', JSON.stringify({ name: 'sample' }), { tags: { endpoint: 'register' } });
  check(res, { created: (r) => r.status === 201 });
  sleep(1);
}

export function loginScenario() {
  http.post('http://127.0.0.1:8765/login', JSON.stringify({ name: 'sample' }), { tags: { endpoint: 'login' } });
  sleep(2);
}

export function tokenScenario() {
  tokenFlow('sample');
  sleep(1);
}
