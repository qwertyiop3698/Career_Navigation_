import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { BASE_URL } from '../config';

const TOKEN_KEY = "access_token";

console.log("[API] BASE_URL", BASE_URL);

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function setAuthToken(token) {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common.Authorization;
  }
}

export async function login(payload) {
  const response = await apiClient.post('/api/v1/auth/login', payload);
  return response.data;
}

export async function signup(payload) {
  const response = await apiClient.post('/api/v1/auth/signup', payload);
  return response.data;
}

export async function getMe() {
  const response = await apiClient.get('/api/v1/auth/me');
  return response.data;
}

export async function createUserProfile(payload) {
  const response = await apiClient.post('/api/v1/users/profile', payload);
  return response.data;
}

export async function updateGithubProfile(payload) {
  const response = await apiClient.patch('/api/v1/users/me/github', payload);
  return response.data;
}

export async function createCareerPath(payload) {
  const response = await apiClient.post('/api/v1/agent/career-path', payload);
  return response.data;
}

export async function getRoleSkills(jobRole, limit = 6) {
  const response = await apiClient.get('/api/v1/trends/role-skills', {
    params: { job_role_category: jobRole, limit },
  });
  return response.data;
}

export async function createRoadmap(payload) {
  const response = await apiClient.post('/api/v1/roadmaps', payload);
  return response.data;
}

export async function getMyRoadmap() {
  const response = await apiClient.get('/api/v1/roadmaps/me');
  return response.data;
}

export async function toggleRoadmapTask(taskId) {
  const response = await apiClient.patch(`/api/v1/roadmaps/tasks/${taskId}/toggle`);
  return response.data;
}

export async function getMyRoadmapProgress() {
  const response = await apiClient.get('/api/v1/roadmaps/me/progress');
  return response.data;
}

export async function getCertificationBetaOptions(jobTarget) {
  const response = await apiClient.get('/api/v1/roadmaps/certifications/beta', {
    params: { job_target: jobTarget },
  });
  return response.data;
}

export async function includeCertificationInRoadmap(code) {
  const response = await apiClient.post(`/api/v1/roadmaps/me/certifications/${code}/include`);
  return response.data;
}

export async function submitRoadmapReassessment(payload) {
  const response = await apiClient.post('/api/v1/roadmaps/me/reassessments', payload);
  return response.data;
}

export async function submitProjectForEvaluation(payload) {
  const response = await apiClient.post('/api/v1/projects/submissions', payload);
  return response.data;
}

export async function requestProjectAiReview(submissionId) {
  const response = await apiClient.post(`/api/v1/projects/submissions/${submissionId}/ai-review`);
  return response.data;
}
