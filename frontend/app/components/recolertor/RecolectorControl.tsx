/* eslint-disable react-hooks/exhaustive-deps */
"use client";
import React, { useState, useEffect } from "react";
import Toast from '../toast/Toast';
import ConfirmationModal from '../confirmation/ConfirmationModal';
import { detectHost } from "../../api";

interface Recolector {
  id: number;
  nombre: string;
  cedula: string;
  telefono: string;
  es_referido: boolean;
}

interface EstadisticasRecolector {
  recolector_id: number;
  nombre: string;
  tickets_count: number;
}

interface Referido {
  id: number;
  cedula: string;
  nombre: string;
  telefono: string;
  estado: string;
  municipio: string;
  parroquia: string;
  fecha_registro: string;
}

interface ReferidosData {
  recolector: {
    id: number;
    nombre: string;
    total_referidos: number;
  };
  referidos: Referido[];
}

interface Estado {
  codigo_estado: string;
  estado: string;
}

const RecolectorControl: React.FC = () => {
  const [recolectores, setRecolectores] = useState<Recolector[]>([]);
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedRecolector, setSelectedRecolector] = useState<Recolector | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [recolectoresPerPage] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [newRecolector, setNewRecolector] = useState({ nombre: "", cedula: "", telefono: "", es_referido: false });

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'success' | 'error' | 'info'>('info');
  const [isConfirmationModalVisible, setIsConfirmationModalVisible] = useState(false);
  const [recolectorToDelete, setRecolectorToDelete] = useState<number | null>(null);
  const [estadisticas, setEstadisticas] = useState<EstadisticasRecolector[]>([]);
  const [isEstadisticasModalOpen, setIsEstadisticasModalOpen] = useState(false);
  const [APIHost, setAPIHost] = useState<string | null>(null);
  const [selectedRecolectorId, setSelectedRecolectorId] = useState<number | null>(null);
  const [referidosData, setReferidosData] = useState<ReferidosData | null>(null);
  const [estadoFiltro, setEstadoFiltro] = useState<string>("");
  const [isDownloading, setIsDownloading] = useState(false);
  const [estados, setEstados] = useState<Estado[]>([]);

  useEffect(() => {
    fetchHost();
  }, []);

  useEffect(() => {
    if (APIHost) {
      fetchRecolectores();
      fetchEstados();
    }
  }, [APIHost, currentPage, searchTerm]);

  const fetchRecolectores = async () => {
    if (!APIHost) return;
    
    const query = new URLSearchParams({
      skip: ((currentPage - 1) * recolectoresPerPage).toString(),
      limit: recolectoresPerPage.toString(),
      ...(searchTerm && { search: searchTerm }),
    }).toString();

    try {
      const response = await fetch(`${APIHost}/api/recolectores/?${query}`);
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      const data = await response.json();
      if (Array.isArray(data.items)) {
        setRecolectores(data.items);
        setTotalPages(Math.ceil(data.total / recolectoresPerPage));
      } else {
        setRecolectores(data);
        setTotalPages(Math.ceil(data.length / recolectoresPerPage));
      }
    } catch (error) {
      console.error("Error fetching recolectores:", error);
      setRecolectores([]);
      setTotalPages(1);
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

  const fetchEstados = async () => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/estados`);
      if (!response.ok) {
        throw new Error('Error fetching estados');
      }
      const data = await response.json();
      setEstados(data);
    } catch (error) {
      console.error("Error fetching estados:", error);
      setToastMessage("Error obteniendo estados");
      setToastType("error");
    }
  };

  const handleDelete = async () => {
    if (!recolectorToDelete || !APIHost) return;
    await fetch(`${APIHost}/api/recolectores/${recolectorToDelete}`, { method: "DELETE" });
    setRecolectorToDelete(null);
    setIsConfirmationModalVisible(false);
    fetchRecolectores();
    setToastMessage("Recolector eliminado exitosamente");
    setToastType("success");
  };

  const handleCreate = async () => {
    if (!APIHost) return;
    
    try {
      const response = await fetch(`${APIHost}/api/recolectores`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(newRecolector)
      });
  
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      setNewRecolector({ nombre: "", cedula: "", telefono: "", es_referido: false });
      fetchRecolectores();
      closeModal();
      setToastMessage("Recolector creado exitosamente");
      setToastType("success");
    } catch (error) {
      console.error("Error creating recolector:", error);
      setToastMessage("Error creando recolector");
      setToastType("error");
    }
  };

  const handleUpdate = async (recolector: Recolector) => {
    if (!APIHost) return;
    
    try {
      const response = await fetch(`${APIHost}/api/recolectores/${recolector.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(recolector)
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      fetchRecolectores();
      closeModal();
      setToastMessage("Recolector actualizado exitosamente");
      setToastType("success");
    } catch (error) {
      console.error("Error updating recolector:", error);
      setToastMessage("Error actualizando recolector");
      setToastType("error");
    }
  };

  const openModal = (recolector: Recolector | null = null) => {
    setSelectedRecolector(recolector);
    setIsEditing(!!recolector);
    setModalIsOpen(true);
  };

  const closeModal = () => {
    setModalIsOpen(false);
    setSelectedRecolector(null);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // Reset to the first page on search
  };

  const paginate = (pageNumber: number) => {
    if (pageNumber < 1) {
      setCurrentPage(1);
    } else if (pageNumber > totalPages) {
      setCurrentPage(totalPages);
    } else {
      setCurrentPage(pageNumber);
    }
    fetchRecolectores();
  };

  const fetchEstadisticas = async (recolectorId?: number) => {
    let url = `${APIHost}/api/recolectores/estadisticas/`;
    if (recolectorId) {
      url += `?recolector_id=${recolectorId}`;
    }
    if (estadoFiltro) {
      url += `${recolectorId ? '&' : '?'}codigo_estado=${estadoFiltro}`;
    }

    try {
      const response = await fetch(url);
      const data: EstadisticasRecolector[] = await response.json();
      setEstadisticas(data);
      setIsEstadisticasModalOpen(true);
      
      if (recolectorId) {
        setSelectedRecolectorId(recolectorId);
        await fetchReferidos(recolectorId);
      } else {
        setSelectedRecolectorId(null);
        setReferidosData(null);
      }
    } catch (error) {
      console.error("Error fetching estadísticas:", error);
      setToastMessage("Error obteniendo estadísticas");
      setToastType("error");
    }
  };

  const fetchReferidos = async (recolectorId: number) => {
    try {
      let url = `${APIHost}/api/recolectores/${recolectorId}/referidos`;
      if (estadoFiltro) {
        url += `?codigo_estado=${estadoFiltro}`;
      }
      const response = await fetch(url);
      const data: ReferidosData = await response.json();
      setReferidosData(data);
    } catch (error) {
      console.error("Error fetching referidos:", error);
      setToastMessage("Error obteniendo referidos");
      setToastType("error");
    }
  };

  const handleEstadoFiltroChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newEstado = e.target.value;
    setEstadoFiltro(newEstado);
    await fetchEstadisticas(selectedRecolectorId || undefined);
  };

  const downloadReferidosExcel = async (recolectorId: number) => {
    if (!APIHost) return;
    
    try {
      setIsDownloading(true);
      let url = `${APIHost}/download/excel/recolector-referidos/${recolectorId}`;
      if (estadoFiltro) {
        url += `?codigo_estado=${estadoFiltro}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Error al descargar el archivo');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `referidos_${recolectorId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      setToastMessage("Archivo descargado exitosamente");
      setToastType("success");
    } catch (error) {
      console.error("Error downloading file:", error);
      setToastMessage("Error al descargar el archivo");
      setToastType("error");
    } finally {
      setIsDownloading(false);
    }
  };

  const closeEstadisticasModal = () => {
    setIsEstadisticasModalOpen(false);
    setEstadisticas([]);
  };

  return (
    <div className="p-4">
      <h2>Control de Recolectores</h2>
      <button onClick={() => openModal()} className="btn btn-primary mb-4">Crear Nuevo Recolector</button>
      <button onClick={() => fetchEstadisticas()} className="btn btn-secondary mb-4 ml-2">Ver Estadísticas Generales</button>
      <input
        type="text"
        placeholder="Buscar..."
        value={searchTerm}
        onChange={handleSearchChange}
        className="input input-bordered mb-4"
      />
      <div className="pagination mb-4 flex justify-center">
        <button onClick={() => paginate(1)} className="btn btn-primary mr-1">{"<<"}</button>
        <button onClick={() => paginate(currentPage - 1)} className="btn btn-primary mr-1">{"<"}</button>
        <span className="btn btn-disabled mr-1">Página {currentPage} de {totalPages}</span>
        <button onClick={() => paginate(currentPage + 1)} className="btn btn-primary mr-1">{">"}</button>
        <button onClick={() => paginate(totalPages)} className="btn btn-primary">{">>"}</button>
      </div>
      <table className="table-auto w-full">
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Cédula</th>
            <th>Teléfono</th>
            <th>Referido</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {recolectores.map((recolector) => (
            <tr key={recolector.id}>
              <td>{recolector.id}</td>
              <td>{recolector.nombre}</td>
              <td>{recolector.cedula}</td>
              <td>{recolector.telefono}</td>
              <td>{recolector.es_referido ? "Sí" : "No"}</td>
              <td>
                <button className="btn btn-primary mr-2" onClick={() => openModal(recolector)}>Editar</button>
                <button className="btn btn-danger mr-2" onClick={() => { setRecolectorToDelete(recolector.id); setIsConfirmationModalVisible(true); }}>Eliminar</button>
                <button className="btn btn-info" onClick={() => fetchEstadisticas(recolector.id)}>Ver Estadísticas</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {modalIsOpen && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-button" onClick={closeModal}>×</button>
            <h2>{isEditing ? "Editar Recolector" : "Crear Recolector"}</h2>
            <input
              type="text"
              placeholder="Nombre"
              value={isEditing && selectedRecolector ? selectedRecolector.nombre : newRecolector.nombre}
              onChange={(e) => {
                if (isEditing && selectedRecolector) {
                  setSelectedRecolector({ ...selectedRecolector, nombre: e.target.value });
                } else {
                  setNewRecolector({ ...newRecolector, nombre: e.target.value });
                }
              }}
              className="input input-bordered w-full mb-2"
            />
            <input
              type="text"
              placeholder="Cédula"
              value={isEditing && selectedRecolector ? selectedRecolector.cedula : newRecolector.cedula}
              onChange={(e) => {
                if (isEditing && selectedRecolector) {
                  setSelectedRecolector({ ...selectedRecolector, cedula: e.target.value });
                } else {
                  setNewRecolector({ ...newRecolector, cedula: e.target.value });
                }
              }}
              className="input input-bordered w-full mb-2"
            />
            <input
              type="text"
              placeholder="Teléfono"
              value={isEditing && selectedRecolector ? selectedRecolector.telefono : newRecolector.telefono}
              onChange={(e) => {
                if (isEditing && selectedRecolector) {
                  setSelectedRecolector({ ...selectedRecolector, telefono: e.target.value });
                } else {
                  setNewRecolector({ ...newRecolector, telefono: e.target.value });
                }
              }}
              className="input input-bordered w-full mb-2"
            />
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <input
                type="checkbox"
                checked={isEditing && selectedRecolector ? selectedRecolector.es_referido : newRecolector.es_referido}
                onChange={(e) => {
                  if (isEditing && selectedRecolector) {
                    setSelectedRecolector({ ...selectedRecolector, es_referido: e.target.checked });
                  } else {
                    setNewRecolector({ ...newRecolector, es_referido: e.target.checked });
                  }
                }}
              />
              Es Referido
            </label>
            <button onClick={isEditing ? () => handleUpdate(selectedRecolector!) : handleCreate} className="btn btn-primary">
              {isEditing ? "Actualizar Recolector" : "Crear Recolector"}
            </button>
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
          message="¿Estás seguro de que quieres eliminar este recolector?"
          onConfirm={handleDelete}
          onCancel={() => setIsConfirmationModalVisible(false)}
        />
      )}
      {isEstadisticasModalOpen && (
        <div className="modal-overlay" onClick={closeEstadisticasModal}>
          <div className="modal-content max-w-7xl w-full p-6" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-button" onClick={closeEstadisticasModal}>×</button>
            <h2 className="text-xl font-bold mb-4">Estadísticas de Recolectores</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Filtrar por Estado:</label>
              <select
                value={estadoFiltro}
                onChange={handleEstadoFiltroChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              >
                <option value="">Todos los estados</option>
                {estados.map(estado => (
                  <option key={estado.codigo_estado} value={estado.codigo_estado}>
                    {estado.estado}
                  </option>
                ))}
              </select>
            </div>

            <div className="overflow-x-auto">
              <table className="table-auto w-full mb-4">
                <thead>
                  <tr>
                    <th>ID Recolector</th>
                    <th>Nombre</th>
                    <th>Cantidad de Tickets</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {estadisticas.map((stat) => (
                    <tr key={stat.recolector_id} className={selectedRecolectorId === stat.recolector_id ? 'bg-blue-100' : ''}>
                      <td>{stat.recolector_id}</td>
                      <td>{stat.nombre}</td>
                      <td>{stat.tickets_count}</td>
                      <td>
                        <button 
                          onClick={() => fetchEstadisticas(stat.recolector_id)}
                          className="btn btn-sm btn-primary mr-2"
                        >
                          Ver Referidos
                        </button>
                        <button
                          onClick={() => downloadReferidosExcel(stat.recolector_id)}
                          className="btn btn-sm btn-secondary"
                          disabled={isDownloading}
                        >
                          {isDownloading ? 'Descargando...' : 'Descargar Excel'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {referidosData && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold mb-3">
                  Referidos de {referidosData.recolector.nombre}
                  <span className="text-sm text-gray-600 ml-2">
                    (Total: {referidosData.recolector.total_referidos})
                  </span>
                </h3>
                <div className="overflow-x-auto">
                  <table className="table-auto w-full">
                    <thead>
                      <tr>
                        <th>Cédula</th>
                        <th>Nombre</th>
                        <th>Teléfono</th>
                        <th>Estado</th>
                        <th>Municipio</th>
                        <th>Parroquia</th>
                        <th>Fecha Registro</th>
                      </tr>
                    </thead>
                    <tbody>
                      {referidosData.referidos.map((referido) => (
                        <tr key={referido.id}>
                          <td>{referido.cedula}</td>
                          <td>{referido.nombre}</td>
                          <td>{referido.telefono}</td>
                          <td>{referido.estado}</td>
                          <td>{referido.municipio}</td>
                          <td>{referido.parroquia}</td>
                          <td>{new Date(referido.fecha_registro).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RecolectorControl;
