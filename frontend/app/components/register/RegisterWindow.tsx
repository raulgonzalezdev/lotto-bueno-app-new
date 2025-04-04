/* eslint-disable @next/next/no-img-element */

import React, { useState, useEffect } from 'react';
import LoginModal from '../login/Login';
import Toast from '../toast/Toast';
import ConfirmationModal from '../confirmation/ConfirmationModal';
import { detectHost } from "../../api";

interface RegisterWindowProps {
  title: string;
  subtitle: string;
  imageSrc: string;
  setCurrentPage: React.Dispatch<React.SetStateAction<"WELCOME" | "ELECTORES" | "TICKETS" | "STATUS" | "ADD" | "SETTINGS" | "USERS" | "RECOLECTORES" | "REGISTER">>;
  onAdminLogin: (isAdmin: boolean) => void;
}

const RegisterWindow: React.FC<RegisterWindowProps> = ({ title, subtitle, imageSrc, setCurrentPage, onAdminLogin }) => {
  const [isLoginModalVisible, setIsLoginModalVisible] = useState(false);
  const [isQRModalVisible, setIsQRModalVisible] = useState(false);
  const [qrCode, setQRCode] = useState<string | null>(null);
  const [referidos, setReferidos] = useState([]);
  const [formData, setFormData] = useState({ cedula: "", operador: "0414", telefono: "", referido_id: 1 });
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'success' | 'error' | 'info'>('info');
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isConfirmationModalVisible, setIsConfirmationModalVisible] = useState(false);
  const [ticketMessage, setTicketMessage] = useState("");
  const [fullnumberMessage, setFullnumberMessage] = useState("");
  const [APIHost, setAPIHost] = useState<string | null>(null);
  

  const companyPhoneContact = process.env.COMPANY_PHONE_CONTACT || '584262831867';

  useEffect(() => {
    fetchHost();
  }, []);

  useEffect(() => {
    if (APIHost) {
      fetchReferidos();
    }
  }, [APIHost]);

  const fetchReferidos = async () => {
    try {
      const response = await fetch(`${APIHost}/api/recolectores`);
      const data = await response.json();
      setReferidos(data.items);
    } catch (error) {
      console.error("Error fetching referidos:", error);
    }
  };

  const fetchHost = async () => {
    try {
      const host = await detectHost();
      setAPIHost(host);
    } catch (error) {
      console.error("Error detecting host:", error);
      setAPIHost(process.env.HOST || 'http://localhost:8000');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleOpenLoginModal = () => {
    setIsLoginModalVisible(true);
  };

  const handleCloseLoginModal = () => {
    setIsLoginModalVisible(false);
  };

  const handleOpenQRModal = (qr: string) => {
    setQRCode(qr);
    setIsQRModalVisible(true);
  };

  const handleCloseQRModal = () => {
    setIsQRModalVisible(false);
    setQRCode(null);
    window.location.href = `https://wa.me/${companyPhoneContact}?text=/start%0A${formData.cedula}. Hola, soy ${ticketMessage} con cédula ${formData.cedula}. Este es mi numero telefonico número ${fullnumberMessage} para Lotto Bueno.`;
  };

  const handleConfirmRegisterAnother = () => {
    setFormData({ cedula: "", operador: "0414", telefono: "", referido_id: 1 });
    setIsConfirmationModalVisible(false);
  };

  const handleCancelRegisterAnother = () => {
    setIsConfirmationModalVisible(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setToastMessage(null);

    const fullPhoneNumber = `58${formData.operador.slice(1)}${formData.telefono}`;
    setFullnumberMessage(fullPhoneNumber);
    if (!/^58\d{10}$/.test(fullPhoneNumber)) {
      setToastMessage("El número de teléfono debe tener 10 dígitos después del operador.");
      setToastType('error');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${APIHost}/generate_tickets`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          cedula: formData.cedula,
          telefono: fullPhoneNumber,
          referido_id: formData.referido_id || 1
        })
      });

      const data = await response.json();
      if (response.status === 200) {
        if (data.status === "success") {
          setTicketMessage(data.message);
          if (data.qr_code) {
            handleOpenQRModal(data.qr_code);
          }
          setToastMessage(data.message);
          setToastType('success');
        } else if (data.message.includes('404 Client Error: Not Found')) {
          setToastMessage("La cédula no es válida y debe estar inscrita en el registro electoral.");
          setToastType('info');
        } else {
          setToastMessage(data.message || "Error generando el ticket. Por favor, intenta de nuevo.");
          setToastType('info');
        }
      } else {
        setToastMessage("Error generando el ticket. Por favor, intenta de nuevo.");
        setToastType('error');
      }
    } catch (error) {
      console.error("Error generating ticket:", error);
      setToastMessage("Error generando el ticket. Por favor, intenta de nuevo.");
      setToastType('error');
    }

    setIsLoading(false);
  };

  const filteredReferidos = referidos.filter((referido: any) => 
    `${referido.cedula} ${referido.nombre}`.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="welcome-page">
      <div className="register-page p-4 flex flex-col items-center">
        
        <img src={imageSrc} width={381} height={162} className="footer-logo" alt="Logo" />
        <h1 className="text-4xl font-bold mb-2 text-center text-white">{title}</h1>
        <h2 className="text-xl mb-6 text-center text-white">{subtitle}</h2>
        <form className="space-y-4 w-full max-w-md" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-gray-700 text-white">Promotor</label>
            <input 
              type="text"
              placeholder="Buscar promotor..."
              className="inputField mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <select 
              name="referido_id"
              className="inputField mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              onChange={handleInputChange}
              value={formData.referido_id}
            >
              <option value="1">ninguno</option>
              {filteredReferidos.map((referido: any) => (
                <option key={referido.id} value={referido.id}>
                  {`${referido.cedula} - ${referido.nombre}`}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 text-white">Cédula</label>
            <input 
              type="text" 
              name="cedula"
              className="inputField mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" 
              value={formData.cedula}
              onChange={handleInputChange}
            />
          </div>
          <div className="flex items-center">
            
            <div className="ml-2">
              <label className="block text-sm font-medium text-gray-700 text-white">Operador</label>
              <select 
                name="operador"
                className="inputField mt-1 block px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                onChange={handleInputChange}
                value={formData.operador}
              >
                <option value="0414">0414</option>
                <option value="0424">0424</option>
                <option value="0416">0416</option>
                <option value="0426">0426</option>
                <option value="0412">0412</option>
              </select>
            </div>
            <div className="flex-grow">
              <label className="block text-sm font-medium text-gray-700 text-white">Teléfono</label>
              <input 
                type="text" 
                name="telefono"
                placeholder="Ingrese el número de teléfono"
                className="inputField mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" 
                value={formData.telefono}
                onChange={handleInputChange}
              />
            </div>
          </div>
          <div className="flex justify-center">
            <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-700" disabled={isLoading}>
              {isLoading ? <span className="spinner"></span> : "Registrar"}
            </button>
          </div>
        </form>
        <div className="mt-4 text-center">
          <button onClick={handleOpenLoginModal} className="text-blue-500 hover:underline">
            Ir al Dashboard
          </button>
        </div>
        <LoginModal
          isVisible={isLoginModalVisible}
          onClose={handleCloseLoginModal}
          onAdminLogin={onAdminLogin}
          setCurrentPage={setCurrentPage}
          title={title}
          subtitle={subtitle}
          imageSrc={imageSrc}
        />
        {isQRModalVisible && qrCode && (
          <div className="modal-overlay" onClick={handleCloseQRModal}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close-button" onClick={handleCloseQRModal}>×</button>
              <h2>Ticket Generado</h2>
              <img src={`data:image/png;base64,${qrCode}`} alt="QR Code" />
              <p>El ticket ha sido generado exitosamente.</p>
              <a
                href={`https://wa.me/${companyPhoneContact}?text=/start%0A${formData.cedula}. Hola, soy ${ticketMessage} con cédula ${formData.cedula}. Este es mi numero telefonico número ${fullnumberMessage} para Lotto Bueno.`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-700 mt-4 inline-block"
              >
                Enviar mensaje por WhatsApp
              </a>
            </div>
          </div>
        )}
        {toastMessage && (
          <Toast 
            message={toastMessage}
            type={toastType}
            onClose={() => setToastMessage(null)}
          />
        )}
        {isConfirmationModalVisible && (
          <ConfirmationModal
            message="¿Quieres registrar otro ticket?"
            onConfirm={handleConfirmRegisterAnother}
            onCancel={handleCancelRegisterAnother}
          />
        )}
      </div>
    </div>
  );
};

export default RegisterWindow;
