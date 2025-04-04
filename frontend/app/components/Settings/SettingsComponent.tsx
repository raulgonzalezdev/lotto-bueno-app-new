/* eslint-disable react-hooks/exhaustive-deps */

"use client";
import React, { useState, useEffect } from "react";
import { detectHost } from "../../api";
import {
  SettingsConfiguration,
  TextFieldSetting,
  ImageFieldSetting,
  CheckboxSetting,
  ColorSetting,
  BaseSettings,
  Settings,
  SelectSetting,
  NumberFieldSetting,
} from "./types";
import { FaPaintBrush } from "react-icons/fa";
import { IoChatbubbleSharp } from "react-icons/io5";
import { FaCheckCircle } from "react-icons/fa";
import { MdCancel } from "react-icons/md";
import { LuMenu } from "react-icons/lu";

import TextFieldComponent from "./TextFieldComponent";
import ImageFieldComponent from "./ImageFieldComponent";
import ColorFieldComponent from "./ColorFieldComponent";
import SelectComponent from "./SelectFieldComponent";
import CheckComponent from "./CheckFieldComponent";
import NumberFieldComponent from "./NumberFieldComponent";

import SettingButton from "./SettingsButton";

interface SettingsComponentProps {
  settingTemplate: string;
  setSettingTemplate: (s: string) => void;
  baseSetting: Settings;
  setBaseSetting: (b: any) => void;
}

const SettingsComponent: React.FC<SettingsComponentProps> = ({
  settingTemplate,
  setSettingTemplate,
  baseSetting,
  setBaseSetting,
}) => {
  const [setting, setSetting] = useState<"Customization" | "Chat" | "">("Customization");
  const [currentSettingsConfig, setCurrentSettingsConfig] = useState<SettingsConfiguration>(
    baseSetting[settingTemplate] ?? { Customization: { title: "", description: "", settings: {} }, Chat: { title: "", description: "", settings: {} } }
  );

  const [APIHost, setAPIHost] = useState<string | null>(null);
  const [availableTemplate, setAvailableTemplate] = useState<string[]>([]);

  useEffect(() => {
    const templates = Object.keys(baseSetting)
      .filter((key) => key !== "currentTemplate" && !["selectedTheme", "themes"].includes(key));
    setAvailableTemplate(templates);
    fetchHost();
  }, [baseSetting]);

  const fetchHost = async () => {
    try {
      const host = await detectHost();
      setAPIHost(host);
    } catch (error) {
      console.error("Error detecting host:", error);
      setAPIHost(process.env.HOST || 'http://localhost:8000');
    }
  };

  const fetchCurrentSettings = async () => {
    const response = await fetch(`${APIHost}/api/settings`);
    const data = await response.json();
    setBaseSetting(data);
    setCurrentSettingsConfig(data[settingTemplate] ?? { Customization: { title: "", description: "", settings: {} }, Chat: { title: "", description: "", settings: {} } });
    setSettingTemplate(data.currentTemplate);
  };

  const iconSize = 20;

  const applyChanges = async () => {
    const updatedSettings = {
      ...baseSetting,
      [settingTemplate]: currentSettingsConfig,
      currentTemplate: settingTemplate,
    };
    setBaseSetting(updatedSettings);
    await fetch(`${APIHost}/api/settings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updatedSettings),
    });
  };

  const revertChanges = () => {
    setCurrentSettingsConfig(baseSetting[settingTemplate] ?? { Customization: { title: "", description: "", settings: {} }, Chat: { title: "", description: "", settings: {} } });
  };

  const renderSettingComponent = (
    title: any,
    setting_type: TextFieldSetting | ImageFieldSetting | CheckboxSetting | ColorSetting | SelectSetting | NumberFieldSetting
  ) => {
    if (setting === "") {
      return null;
    }

    switch (setting_type.type) {
      case "text":
        return (
          <TextFieldComponent
            title={title}
            setting={setting}
            TextFieldSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      case "image":
        return (
          <ImageFieldComponent
            title={title}
            setting={setting}
            ImageFieldSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      case "check":
        return (
          <CheckComponent
            title={title}
            setting={setting}
            CheckboxSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      case "select":
        return (
          <SelectComponent
            title={title}
            setting={setting}
            SelectSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      case "color":
        return (
          <ColorFieldComponent
            title={title}
            setting={setting}
            ColorSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      case "number":
        return (
          <NumberFieldComponent
            title={title}
            setting={setting}
            NumberFieldSetting={setting_type}
            settingsConfig={currentSettingsConfig}
            setSettingsConfig={setCurrentSettingsConfig}
          />
        );
      default:
        return null;
    }
  };

  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const name = e.target.value;
    setSettingTemplate(name);
    setCurrentSettingsConfig(baseSetting[name] ?? { Customization: { title: "", description: "", settings: {} }, Chat: { title: "", description: "", settings: {} } });
  };

  return (
    <div className="flex justify-between items-start gap-5">
      {/* Setting Options */}
      <div className="hidden lg:flex lg:flex-col gap-5 lg:w-1/4">
        <div className="flex flex-col justify-center items-center gap-5">
          <p className="md:text-base lg:text-lg text-text-alt-verba">Settings</p>
          <div className="flex flex-col w-full bg-bg-alt-verba p-5 rounded-lg shadow-lg gap-2">
            <SettingButton
              Icon={FaPaintBrush}
              iconSize={iconSize}
              title="Personaliza App"
              currentSetting={setting}
              setSetting={setSetting}
              setSettingString="Customization"
            />
         
            <SettingButton
              Icon={IoChatbubbleSharp}
              iconSize={iconSize}
              title="Configuraciones de chat"
              currentSetting={setting}
              setSetting={setSetting}
              setSettingString=""
            />
          </div>
        </div>
        {setting != "" && currentSettingsConfig && (
          <div className="sm:hidden md:flex flex-col justify-center items-center gap-5">
            <p className="md:text-base lg:text-lg text-text-alt-verba">Description</p>
            <div className="flex flex-col w-full bg-bg-alt-verba p-5 rounded-lg shadow-lg gap-2">
              <p className="sm:text-xs md:text-sm lg:text-base">
                {currentSettingsConfig[setting] ? currentSettingsConfig[setting].description : ""}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Configuration Options */}
      <div className="flex flex-col lg:justify-center justify-start lg:items-center items-start gap-5 w-full lg:w-3/4">
        <div className="flex flex-row gap-2 items-center justify-center w-full">
          <div className="lg:hidden sm:flex md:ml-4 sm:mr-8">
            <ul className="menu menu-sm sm:menu-horizontal bg-base-200 rounded-box bg-bg-alt-verba z-40">
              <li>
                <details>
                  <summary>
                    <LuMenu size={15} /> Ajustes
                  </summary>
                  <ul className="bg-bg-alt-verba">
                    <li onClick={() => setSetting("Customization")}>
                      <a>Personalizar App</a>
                    </li>
                    <li onClick={() => setSetting("Chat")}>
                      <a>Configuraciones de chat</a>
                    </li>
                  </ul>
                </details>
              </li>
            </ul>
          </div>
          <p className="sm:hidden md:flex text-lg text-text-alt-verba">Configuracion</p>
          <select
            value={settingTemplate}
            onChange={handleTemplateChange}
            className="select select-md lg:select-sm text-xs bg-bg-alt-verba text-text-verba"
          >
            {availableTemplate.map((template) => (
              <option key={"Template" + template} value={template}>
                {template}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col w-full bg-bg-alt-verba p-10 rounded-lg shadow-lg h-[70vh] gap-2 overflow-y-scroll">
          <p className="font-bold text-2xl lg:mb-5">{setting}</p>
          {setting != "" && currentSettingsConfig && (
            <div className="lg:hidden flex flex-col items-start gap-5 mb-5">
              <p className="md:text-base lg:text-lg text-text-alt-verba">Descricion</p>
              <div className="flex flex-col w-full gap-2">
                <p className="sm:text-xs md:text-sm lg:text-base">
                  {currentSettingsConfig[setting] ? currentSettingsConfig[setting].description : ""}
                </p>
              </div>
            </div>
          )}
          <div className="flex-coll gap-4 grid sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {setting &&
              currentSettingsConfig &&
              Object.entries(currentSettingsConfig[setting].settings).map(([key, settingValue]) =>
                renderSettingComponent(key, settingValue)
              )}
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <button
              onClick={applyChanges}
              className="btn flex items-center justify-center border-none text-text-verba bg-secondary-verba hover:bg-button-hover-verba"
            >
              <FaCheckCircle />
              <p className="">Aplicar</p>
            </button>
            <button
              onClick={revertChanges}
              className="btn flex items-center justify-center border-none text-text-verba bg-warning-verba hover:bg-button-hover-verba"
            >
              <MdCancel />
              <p className="">Reiniciar</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsComponent;
