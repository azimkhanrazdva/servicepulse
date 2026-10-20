import React from "react";
import { createRoot } from "react-dom/client";
import { PublicApp } from "./PublicApp";
import "./style.css";
import "./phase5.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PublicApp />
  </React.StrictMode>,
);
