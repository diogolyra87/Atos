import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import Cliente from "./Cliente";
import CriarSenha from "./CriarSenha";
import SolicitarAcesso from "./SolicitarAcesso";
import EscolhaPlano from "./EscolhaPlano";
import "./responsivo.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/cliente" element={<Cliente />} />
      <Route path="/criar-senha" element={<CriarSenha />} />
      <Route path="/solicitar-acesso" element={<SolicitarAcesso />} />
      <Route path="/solicitar-acesso/plano" element={<EscolhaPlano />} />
    </Routes>
  </BrowserRouter>
);