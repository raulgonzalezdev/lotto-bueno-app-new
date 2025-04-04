"use client";
import React, { useState, useEffect } from "react";
import Toast from '../toast/Toast';
import { detectHost } from "../../api";

interface Ticket {
  id: number;
  numero_ticket: string;
  cedula: string;
  nombre: string;
  telefono: string;
  estado: string;
  municipio: string;
  parroquia: string;
  referido_id: number | null;
  validado: boolean;
  ganador: boolean;
}

interface Estado {
  codigo_estado: string;
  estado: string;
}

interface Municipio {
  codigo_municipio: string;
  municipio: string;
}

const SorteoControl: React.FC = () => {
  const [ganadores, setGanadores] = useState<Ticket[]>([]);
  const [cantidadGanadores, setCantidadGanadores] = useState(1);
  const [estado, setEstado] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [estadoDescripcion, setEstadoDescripcion] = useState("");
  const [municipioDescripcion, setMunicipioDescripcion] = useState("");
  const [estados, setEstados] = useState<Estado[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'success' | 'error' | 'info'>('info');
  const [APIHost, setAPIHost] = useState<string | null>(null);

  useEffect(() => {
    fetchHost();
  }, []);

  useEffect(() => {
    if (APIHost) {
      fetchEstados();
    }
  }, [APIHost]);

  useEffect(() => {
    if (APIHost && estado) {
      fetchMunicipios(estado);
    } else {
      setMunicipios([]);
      setMunicipio("");
      setMunicipioDescripcion("");
    }
  }, [APIHost, estado]);

  const fetchHost = async () => {
    try {
      const host = await detectHost();
      setAPIHost(host);
    } catch (error) {
      console.error("Error detecting host:", error);
      setAPIHost(process.env.HOST || 'http://localhost:8000');
    }
  };

  const fetchEstados = async () => {
    if (!APIHost) return;
    
    try {
      const response = await fetch(`${APIHost}/api/estados`);
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      const data = await response.json();
      const estadosOrdenados = data.sort((a: Estado, b: Estado) => 
        a.estado.localeCompare(b.estado, 'es', { sensitivity: 'base' })
      );
      setEstados(estadosOrdenados);
    } catch (error) {
      console.error("Error fetching estados:", error);
      setEstados([{ codigo_estado: "", estado: "No hay estados disponibles" }]);
    }
  };

  const fetchMunicipios = async (codigoEstado: string) => {
    if (!APIHost) return;
    
    try {
      const response = await fetch(`${APIHost}/api/municipios/${encodeURIComponent(codigoEstado)}`);
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      const data = await response.json();
      const municipiosOrdenados = data.sort((a: Municipio, b: Municipio) => 
        a.municipio.localeCompare(b.municipio, 'es', { sensitivity: 'base' })
      );
      setMunicipios(municipiosOrdenados.length > 0 ? municipiosOrdenados : [{ codigo_municipio: "", municipio: "No hay municipios disponibles" }]);
    } catch (error) {
      console.error("Error fetching municipios:", error);
      setMunicipios([{ codigo_municipio: "", municipio: "No hay municipios disponibles" }]);
    }
  };

  const handleSorteo = async () => {
    if (!APIHost) return;
    
    try {
      const estadoDesc = estados.find(e => e.codigo_estado.toString() === estado.toString())?.estado || "";
      const municipioDesc = municipios.find(m => m.codigo_municipio.toString() === municipio.toString())?.municipio || "";

      const body = JSON.stringify({
        cantidad_ganadores: cantidadGanadores,
        estado: estado !== "" && estado !== "Seleccionar Estado" ? estadoDesc : "",
        municipio: municipio !== "" && municipio !== "Seleccionar Municipio" ? municipioDesc : ""
      });

      const response = await fetch(`${APIHost}/api/sorteo/ganadores`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: body
      });

      if (!response.ok) {
        const errorData = await response.json();
        setToastMessage(errorData.message || "Error realizando el sorteo. Por favor, intenta de nuevo.");
        setToastType("error");
        return;
      }

      const data: Ticket[] = await response.json();
      setGanadores(Array.isArray(data) ? data : []);
      setToastMessage("Sorteo realizado exitosamente");
      setToastType("success");
    } catch (error) {
      console.error("Error realizando el sorteo:", error);
      setGanadores([]);
      setToastMessage("Error realizando el sorteo. Por favor, intenta de nuevo.");
      setToastType("error");
    }
  };

  const handleQuitarGanadores = async () => {
    if (!APIHost) return;
    
    try {
      const response = await fetch(`${APIHost}/api/sorteo/quitar_ganadores`, {
        method: "POST"
      });

      if (!response.ok) {
        throw new Error('Error en la respuesta del servidor');
      }

      setGanadores([]);
      setToastMessage("Marca de ganadores eliminada exitosamente");
      setToastType("success");
    } catch (error) {
      console.error("Error quitando la marca de ganadores:", error);
      setToastMessage("Error quitando la marca de ganadores. Por favor, intenta de nuevo.");
      setToastType("error");
    }
  };

  return (
    <div className="p-4">
      <h2>Control de Sorteo de Ganadores</h2>
      <div className="mb-4">
        <label className="block mb-2">Cantidad de Ganadores</label>
        <input
          type="number"
          value={cantidadGanadores}
          onChange={(e) => setCantidadGanadores(parseInt(e.target.value))}
          className="input input-bordered w-full"
        />
      </div>
      <div className="mb-4">
        <label className="block mb-2">Estado</label>
        <select
          value={estado}
          onChange={(e) => {
            setEstado(e.target.value);
            const selectedEstado = estados.find(est => est.codigo_estado === e.target.value);
            setEstadoDescripcion(selectedEstado ? selectedEstado.estado : "");
          }}
          className="input input-bordered w-full"
        >
          <option value="">Seleccionar Estado</option>
          {estados.length > 0 && estados[0].estado !== "No hay estados disponibles" ? (
            estados.map((estado) => (
              <option key={estado.codigo_estado} value={estado.codigo_estado}>{estado.estado}</option>
            ))
          ) : (
            <option value="" disabled>No hay estados disponibles</option>
          )}
        </select>
      </div>
      <div className="mb-4">
        <label className="block mb-2">Municipio</label>
        <select
          value={municipio}
          onChange={(e) => {
            setMunicipio(e.target.value);
            const selectedMunicipio = municipios.find(mun => mun.codigo_municipio === e.target.value);
            setMunicipioDescripcion(selectedMunicipio ? selectedMunicipio.municipio : "");
          }}
          className="input input-bordered w-full"
          disabled={municipios.length === 0 || municipios[0].municipio === "No hay municipios disponibles"}
        >
          <option value="">Seleccionar Municipio</option>
          {municipios.length > 0 && municipios[0].municipio !== "No hay municipios disponibles" ? (
            municipios.map((municipio) => (
              <option key={municipio.codigo_municipio} value={municipio.codigo_municipio}>{municipio.municipio}</option>
            ))
          ) : (
            <option value="" disabled>No hay municipios disponibles</option>
          )}
        </select>
      </div>
      <button onClick={handleSorteo} className="btn btn-primary mr-2">Realizar Sorteo</button>
      <button onClick={handleQuitarGanadores} className="btn btn-danger">Quitar Marca de Ganadores</button>
      {toastMessage && (
        <Toast 
          message={toastMessage}
          type={toastType}
          onClose={() => setToastMessage(null)}
        />
      )}
      <h3 className="mt-4">Ganadores del Sorteo</h3>
      <table className="table-auto w-full mb-4">
        <thead>
          <tr>
            <th>ID</th>
            <th>Número Ticket</th>
            <th>Cédula</th>
            <th>Nombre</th>
            <th>Teléfono</th>
            <th>Estado</th>
            <th>Municipio</th>
          </tr>
        </thead>
        <tbody>
          {ganadores.length > 0 ? (
            ganadores.map((ganador) => (
              <tr key={ganador.id}>
                <td>{ganador.id}</td>
                <td>{ganador.numero_ticket}</td>
                <td>{ganador.cedula}</td>
                <td>{ganador.nombre}</td>
                <td>{ganador.telefono}</td>
                <td>{ganador.estado}</td>
                <td>{ganador.municipio}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={7} className="text-center">No hay ganadores disponibles</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default SorteoControl;
