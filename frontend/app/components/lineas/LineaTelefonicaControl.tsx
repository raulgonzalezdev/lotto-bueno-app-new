/* eslint-disable react-hooks/exhaustive-deps */
"use client";
import React, { useState, useEffect } from "react";
import Toast from '../toast/Toast';
import { detectHost } from "../../api";

interface LineaTelefonica {
  id: number;
  numero: string;
  operador: string;
}

const LineaTelefonicaControl: React.FC = () => {
  const [lineas, setLineas] = useState<LineaTelefonica[]>([]);
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [selectedLinea, setSelectedLinea] = useState<LineaTelefonica | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<'success' | 'error' | 'info'>('info');
  const [currentPage, setCurrentPage] = useState(1);
  const [lineasPerPage] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [APIHost, setAPIHost] = useState<string | null>(null);
  const [newLinea, setNewLinea] = useState({ numero: "", operador: "" });

  useEffect(() => {
    fetchLineas();
    fetchHost();
  }, [currentPage, searchTerm]);

  const fetchLineas = async () => {
    const query = new URLSearchParams({
      skip: ((currentPage - 1) * lineasPerPage).toString(),
      limit: lineasPerPage.toString(),
      ...(searchTerm && { search: searchTerm }),
    }).toString();

    try {
      const response = await fetch(`${APIHost}/api/lineas_telefonicas/?${query}`);
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      const data = await response.json();
      if (Array.isArray(data.items)) {
        setLineas(data.items);
        setTotalPages(Math.ceil(data.total / lineasPerPage));
      } else {
        setLineas(data);
        setTotalPages(Math.ceil(data.length / lineasPerPage));
      }
    } catch (error) {
      console.error("Error fetching lineas:", error);
      setLineas([]);
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

  const openModal = (linea: LineaTelefonica | null) => {
    setSelectedLinea(linea);
    setModalIsOpen(true);
  };

  const closeModal = () => {
    setModalIsOpen(false);
    setSelectedLinea(null);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1); // Reset to the first page on search
  };

  const handleDelete = async (id: number) => {
    await fetch(`/api/lineas_telefonicas/${id}`, { method: "DELETE" });
    fetchLineas();
  };

  const handleCreate = async () => {
    try {
      const response = await fetch(`/api/lineas_telefonicas`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(newLinea)
      });
  
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
    } catch (error) {
      // Si hay un error, reintentar con https
      try {
        const response = await fetch(`/api/lineas_telefonicas`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(newLinea)
        });
  
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
      } catch (retryError) {
        console.error("Error creating linea telefonica:", retryError);
        setToastMessage("Error creando línea telefónica");
        setToastType("error");
        return;
      }
    }
  
    setNewLinea({ numero: "", operador: "" });
    fetchLineas();
    closeModal();
  };

  const handleUpdate = async (linea: LineaTelefonica) => {
    await fetch(`/api/lineas_telefonicas/${linea.id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(linea)
    });
    fetchLineas();
    closeModal();
  };

  const paginate = (pageNumber: number) => {
    if (pageNumber < 1) {
      setCurrentPage(1);
    } else if (pageNumber > totalPages) {
      setCurrentPage(totalPages);
    } else {
      setCurrentPage(pageNumber);
    }
    fetchLineas();
  };

  return (
    <div className="p-4">
      <h2>Control de Líneas Telefónicas</h2>
      <button onClick={() => openModal(null)} className="btn btn-primary mb-4">Crear Nueva Línea</button>
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
      <table className="table-auto w-full mb-4">
        <thead>
          <tr>
            <th>ID</th>
            <th>Número</th>
            <th>Operador</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {lineas.map((linea) => (
            <tr key={linea.id}>
              <td>{linea.id}</td>
              <td>{linea.numero}</td>
              <td>{linea.operador}</td>
              <td>
                <button className="btn btn-primary mr-2" onClick={() => openModal(linea)}>Editar</button>
                <button className="btn btn-danger" onClick={() => handleDelete(linea.id)}>Eliminar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {modalIsOpen && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-button" onClick={closeModal}>×</button>
            <h2>{selectedLinea ? "Editar Línea" : "Crear Nueva Línea"}</h2>
            <form onSubmit={(e) => { e.preventDefault(); selectedLinea ? handleUpdate(selectedLinea) : handleCreate(); }}>
              <div>
                <label className="block text-sm font-medium text-gray-700">Número</label>
                <input
                  type="text"
                  name="numero"
                  value={selectedLinea ? selectedLinea.numero : newLinea.numero}
                  onChange={(e) => {
                    if (selectedLinea) {
                      setSelectedLinea({ ...selectedLinea, numero: e.target.value });
                    } else {
                      setNewLinea({ ...newLinea, numero: e.target.value });
                    }
                  }}
                  className="input input-bordered w-full mb-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Operador</label>
                <input
                  type="text"
                  name="operador"
                  value={selectedLinea ? selectedLinea.operador : newLinea.operador}
                  onChange={(e) => {
                    if (selectedLinea) {
                      setSelectedLinea({ ...selectedLinea, operador: e.target.value });
                    } else {
                      setNewLinea({ ...newLinea, operador: e.target.value });
                    }
                  }}
                  className="input input-bordered w-full mb-2"
                />
              </div>
              <button type="submit" className="btn btn-primary">
                {selectedLinea ? "Guardar Cambios" : "Crear"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LineaTelefonicaControl;
