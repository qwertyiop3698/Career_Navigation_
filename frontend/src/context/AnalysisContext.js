import { createContext, useContext, useMemo, useState } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeRoadmap, setActiveRoadmap] = useState(null);
  const [lastSkills, setLastSkills] = useState(["Python", "SQL", "RAG"]);

  const value = useMemo(
    () => ({
      analysisResult,
      activeRoadmap,
      lastSkills,
      setAnalysisResult,
      setActiveRoadmap,
      setLastSkills,
    }),
    [analysisResult, activeRoadmap, lastSkills],
  );

  return (
    <AnalysisContext.Provider value={value}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used inside AnalysisProvider");
  }
  return context;
}
