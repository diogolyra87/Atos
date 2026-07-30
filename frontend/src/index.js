import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import Cliente from "./Cliente";
import CriarSenha from "./CriarSenha";
import "./responsivo.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/cliente" element={<Cliente />} />
      <Route path="/criar-senha" element={<CriarSenha />} />
    </Routes>
  </BrowserRouter>
);