"use client";

import React, { useState, useEffect } from "react";
import Navbar from "./components/Navigation/NavbarComponent";
import SettingsComponent from "./components/Settings/SettingsComponent";
import ChatComponent from "./components/Chat/ChatComponent";

import WelcomeComponent from "./components/Welcome/WelcomeComponent";
import RegisterWindow from "./components/register/RegisterWindow";
import UserControl from "./components/login/UserControl";
import TicketControl from "./components/ticket/TicketControl";
import RecolectorControl from "./components/recolertor/RecolectorControl";
import LineaTelefonicaControl from "./components/lineas/LineaTelefonicaControl";
import SorteoControl from "./components/sorteo/SorteoControl";

import { Settings } from "./components/Settings/types";

import { RAGConfig } from "./components/RAG/types";
import { detectHost } from "./api";
import { GoogleAnalytics } from "@next/third-parties/google";
import { fonts, FontKey } from "./info";
import PulseLoader from "react-spinners/PulseLoader";


const Home = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentPage, setCurrentPage] = useState<
    "WELCOME" | "ELECTORES" | "TICKETS" | "STATUS" | "ADD" | "SETTINGS" | "USERS" | "RECOLECTORES" | "REGISTER"
  >("WELCOME");
  const [production, setProduction] = useState(false);
  const [gtag, setGtag] = useState("");
  const [settingTemplate, setSettingTemplate] = useState<string>("Default");
  const [baseSetting, setBaseSetting] = useState<Settings | null>(null);
  const [RAGConfig, setRAGConfig] = useState<RAGConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fontKey = baseSetting ? (baseSetting[settingTemplate]?.Customization.settings.font.value as FontKey) : null;
  const fontClassName = fontKey ? fonts[fontKey]?.className || "" : "";

  const [APIHost, setAPIHost] = useState<string | null>(null);

  const handleOutsideClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      // setIsChatVisible(false);
    }
  };

  // Verificar sesión al cargar la página
  useEffect(() => {
    const session = localStorage.getItem('session');
    if (session) {
      const sessionData = JSON.parse(session);
      setIsAdmin(sessionData.isAdmin);
      setCurrentPage(sessionData.lastPage || "ELECTORES");
    }
  }, []);

  // Guardar estado de la sesión cuando cambia
  useEffect(() => {
    if (isAdmin) {
      localStorage.setItem('session', JSON.stringify({
        isAdmin,
        lastPage: currentPage
      }));
    }
  }, [isAdmin, currentPage]);

  const handleLogout = () => {
    setIsAdmin(false);
    localStorage.removeItem('session');
    setCurrentPage("WELCOME");
  };

  const handleAdminChange = (value: string | boolean): void => {
    if (typeof value === "string" && value === "1234") {
      setIsAdmin(true);
      setCurrentPage("ELECTORES");
    } else if (typeof value === "boolean") {
      setIsAdmin(value);
      if (value) {
        setCurrentPage("ELECTORES");
      }
    }
  };

  const fetchCurrentSettings = async (apiHost: string) => {
    try {
      const response = await fetch(`${apiHost}/api/settings`);
      if (response.ok) {
        const data = await response.json();
        setBaseSetting(data);
        setSettingTemplate(data.currentTemplate);
      } else {
        console.error("Failed to fetch settings");
      }
    } catch (error) {
      console.error("Error fetching settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHost = async () => {
    try {
      const host = await detectHost();
      setAPIHost(host);
      await fetchCurrentSettings(host);
    } catch (error) {
      console.error("Error detecting host:", error);
      setAPIHost(null);
      setIsLoading(false);
    }
  };

  const importConfig = async () => {
    if (!APIHost || !baseSetting) {
      return;
    }

    try {
      const payload = {
        config: {
          RAG: RAGConfig,
          SETTING: { selectedTheme: settingTemplate, themes: baseSetting },
        },
      };
      await fetch(`${APIHost}/api/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload.config.SETTING),
      });
    } catch (error) {
      console.error("Failed to update config:", error);
    }
  };


  useEffect(() => {
    fetchHost();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    importConfig();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseSetting, settingTemplate]);

  useEffect(() => {
    if (baseSetting) {
      document.documentElement.style.setProperty(
        "--primary-verba",
        baseSetting[settingTemplate]?.Customization.settings.primary_color.color
      );
      document.documentElement.style.setProperty(
        "--secondary-verba",
        baseSetting[settingTemplate]?.Customization.settings.secondary_color.color
      );
      document.documentElement.style.setProperty(
        "--warning-verba",
        baseSetting[settingTemplate]?.Customization.settings.warning_color.color
      );
      document.documentElement.style.setProperty(
        "--bg-verba",
        baseSetting[settingTemplate]?.Customization.settings.bg_color.color
      );
      document.documentElement.style.setProperty(
        "--bg-alt-verba",
        baseSetting[settingTemplate]?.Customization.settings.bg_alt_color.color
      );
      document.documentElement.style.setProperty(
        "--text-verba",
        baseSetting[settingTemplate]?.Customization.settings.text_color.color
      );
      document.documentElement.style.setProperty(
        "--text-alt-verba",
        baseSetting[settingTemplate]?.Customization.settings.text_alt_color.color
      );
      document.documentElement.style.setProperty(
        "--button-verba",
        baseSetting[settingTemplate]?.Customization.settings.button_color.color
      );
      document.documentElement.style.setProperty(
        "--button-hover-verba",
        baseSetting[settingTemplate]?.Customization.settings.button_hover_color.color
      );
      document.documentElement.style.setProperty(
        "--bg-console-verba",
        baseSetting[settingTemplate]?.Customization.settings.bg_console.color
      );
      document.documentElement.style.setProperty(
        "--text-console-verba",
        baseSetting[settingTemplate]?.Customization.settings.text_console.color
      );
    }
  }, [baseSetting, settingTemplate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen gap-2">
        <PulseLoader loading={true} size={12} speedMultiplier={0.75} />
        <p>Cargando Lotto Bueno</p>
      </div>
    );
  }

  if (!baseSetting) {
    return (
      <div className="flex items-center justify-center h-screen gap-2">
        <p>Error cargando la configuración.</p>
      </div>
    );
  }

  return (
    <div onClick={handleOutsideClick}>
      <main
        className={
          isAdmin
            ? `min-h-screen p-5 bg-bg-verba text-text-verba ${fontClassName}`
            : `fixed inset-0 overflow-y-auto bg-white bg-opacity-75 ${fontClassName}`
        }
        data-theme={
          baseSetting
            ? baseSetting[settingTemplate]?.Customization.settings.theme
            : "light"
        }
      >
        {gtag !== "" && <GoogleAnalytics gaId={gtag} />}

        <div>
          {!isAdmin && currentPage === "WELCOME" && (
            <WelcomeComponent 
              title="Completa tu registro y gana fabulosos premios" 
              subtitle="En tan solo 3 simples pasos podrás convertirte en el ganador o ganadora de #LottoBueno"
              imageSrc={baseSetting[settingTemplate]?.Customization.settings.image.src}
              setCurrentPage={setCurrentPage}
            />
          )}

          {!isAdmin && currentPage === "REGISTER" && (
            <RegisterWindow 
              title={baseSetting[settingTemplate]?.Customization.settings.title.text} 
              subtitle={baseSetting[settingTemplate]?.Customization.settings.subtitle.text}
              imageSrc={baseSetting[settingTemplate]?.Customization.settings.image.src}
              setCurrentPage={setCurrentPage}
              onAdminLogin={handleAdminChange}
            />
          )}

          {isAdmin && (
            <>
              <div className="flex justify-between items-center mb-4">
                <Navbar
                  APIHost={APIHost}
                  production={production}
                  title={baseSetting[settingTemplate]?.Customization.settings.title.text}
                  subtitle={baseSetting[settingTemplate]?.Customization.settings.subtitle.text}
                  imageSrc={baseSetting[settingTemplate]?.Customization.settings.image.src}
                  version="v1.0.1"
                  currentPage={currentPage}
                  setCurrentPage={setCurrentPage}
                />
                <button 
                  onClick={handleLogout}
                  className="btn btn-error btn-sm"
                >
                  Cerrar Sesión
                </button>
              </div>

              {currentPage === "ELECTORES" && (
                <ChatComponent
                  production={production}
                  settingConfig={baseSetting[settingTemplate]}
                  APIHost={APIHost}
                  RAGConfig={RAGConfig}
                  isAdmin={isAdmin}
                  title={baseSetting[settingTemplate]?.Customization.settings.title.text}
                  subtitle={baseSetting[settingTemplate]?.Customization.settings.subtitle.text}
                  imageSrc={baseSetting[settingTemplate]?.Customization.settings.image.src}
                />
              )}

              {currentPage === "STATUS" && <SorteoControl />}
              {currentPage === "SETTINGS" && !production && (
                <SettingsComponent
                  settingTemplate={settingTemplate}
                  setSettingTemplate={setSettingTemplate}
                  baseSetting={baseSetting}
                  setBaseSetting={setBaseSetting}
                />
              )}
              {currentPage === "USERS" && !production && <UserControl />}
              {currentPage === "TICKETS" && !production && <TicketControl />}
              {currentPage === "RECOLECTORES" && !production && <RecolectorControl />}
              {currentPage === "ADD" && !production && <LineaTelefonicaControl />}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default Home;
