import { createContext, useContext } from "react";

export const AuthContext = createContext({
  token: null,
  signIn: async () => {},
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}
