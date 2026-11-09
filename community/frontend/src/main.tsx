import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import Stage from "./Stage";
import { stageFrame } from "./api";
import "./styles.css";
import "./browse.css";
if (stageFrame) document.documentElement.classList.add("stage-frame");
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {window.location.pathname === "/stage" ||
    window.location.pathname === "/舞台" ? (
      <Stage />
    ) : (
      <App />
    )}
  </StrictMode>,
);
