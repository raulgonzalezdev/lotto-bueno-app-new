/* eslint-disable react-hooks/exhaustive-deps */

"use client";
import React, { useState, useEffect } from "react";
import { Elector, Estado, Municipio, Parroquia, CentroVotacion, elector } from './types';

interface ChatComponentProps {
  production: boolean;
  settingConfig: any;
  APIHost: any;
  RAGConfig: any;

  isAdmin: boolean;

  title: string;
  subtitle: string;
  imageSrc: string;
}

const ChatComponent: React.FC<ChatComponentProps> = ({
  production,
  settingConfig,
  APIHost,
  RAGConfig,

  isAdmin,

  title,
  subtitle,
  imageSrc
}) => {
  const [electores, setElectores] = useState<Elector[]>([]);
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [selectedElector, setSelectedElector] = useState<Elector | null>(null);
  const [currentElectorPage, setCurrentElectorPage] = useState(1);
  const [electoresPerPage] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [cedulaSearch, setCedulaSearch] = useState("");

  const [estados, setEstados] = useState<Estado[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [parroquias, setParroquias] = useState<Parroquia[]>([]);
  const [centrosVotacion, setCentrosVotacion] = useState<CentroVotacion[]>([]);
  const [searchError, setSearchError] = useState("");

  const [codigoEstado, setCodigoEstado] = useState("");
  const [codigoMunicipio, setCodigoMunicipio] = useState("");
  const [codigoParroquia, setCodigoParroquia] = useState("");
  const [codigoCentroVotacion, setCodigoCentroVotacion] = useState("");

  const [isDownloading, setIsDownloading] = useState(false);
  const [showDownloadDialog, setShowDownloadDialog] = useState(false);
  const [downloadType, setDownloadType] = useState<{type: string, format: string} | null>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [totalBatches, setTotalBatches] = useState(0);
  const [currentBatch, setCurrentBatch] = useState(0);

  useEffect(() => {
    if (APIHost) {
    fetchEstados();
    fetchElectores();
    fetchTotalElectores();
    }
  }, [APIHost]);

  useEffect(() => {
    if (APIHost && codigoEstado) {
      fetchMunicipios(codigoEstado);
    }
  }, [APIHost, codigoEstado]);

  useEffect(() => {
    if (APIHost && codigoEstado && codigoMunicipio) {
      fetchParroquias(codigoEstado, codigoMunicipio);
    }
  }, [APIHost, codigoEstado, codigoMunicipio]);

  useEffect(() => {
    if (APIHost && codigoEstado && codigoMunicipio && codigoParroquia) {
      fetchCentrosVotacion(codigoEstado, codigoMunicipio, codigoParroquia);
    }
  }, [APIHost, codigoEstado, codigoMunicipio, codigoParroquia]);

  useEffect(() => {
    if (APIHost) {
      fetchElectores();
      fetchTotalElectores();
    }
  }, [APIHost, codigoEstado, codigoMunicipio, codigoParroquia, codigoCentroVotacion, currentElectorPage]);

  const fetchEstados = async () => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/estados`);
      if (!response.ok) {
        throw new Error('Error fetching estados');
      }
      const data = await response.json();
      const estadosOrdenados = data.sort((a: Estado, b: Estado) => 
        a.estado.localeCompare(b.estado, 'es', { sensitivity: 'base' })
      );
      setEstados(estadosOrdenados);
    } catch (error) {
      console.error("Error fetching estados:", error);
      setEstados([]);
    }
  };

  const fetchMunicipios = async (codigoEstado: string) => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/municipios/${codigoEstado}`);
      if (!response.ok) {
        throw new Error('Error fetching municipios');
      }
      const data = await response.json();
      const municipiosOrdenados = data.sort((a: Municipio, b: Municipio) => 
        a.municipio.localeCompare(b.municipio, 'es', { sensitivity: 'base' })
      );
      setMunicipios(municipiosOrdenados);
    } catch (error) {
      console.error("Error fetching municipios:", error);
      setMunicipios([]);
    }
  };

  const fetchParroquias = async (codigoEstado: string, codigoMunicipio: string) => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/parroquias/${codigoEstado}/${codigoMunicipio}`);
      if (!response.ok) {
        throw new Error('Error fetching parroquias');
      }
      const data = await response.json();
      const parroquiasOrdenadas = data.sort((a: Parroquia, b: Parroquia) => 
        a.parroquia.localeCompare(b.parroquia, 'es', { sensitivity: 'base' })
      );
      setParroquias(parroquiasOrdenadas);
    } catch (error) {
      console.error("Error fetching parroquias:", error);
      setParroquias([]);
    }
  };

  const fetchCentrosVotacion = async (codigoEstado: string, codigoMunicipio: string, codigoParroquia: string) => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/centros_votacion/${codigoEstado}/${codigoMunicipio}/${codigoParroquia}`);
      if (!response.ok) {
        throw new Error('Error fetching centros votacion');
      }
      const data = await response.json();
      const centrosOrdenados = data.sort((a: CentroVotacion, b: CentroVotacion) => 
        a.nombre_cv.localeCompare(b.nombre_cv, 'es', { sensitivity: 'base' })
      );
      setCentrosVotacion(centrosOrdenados);
    } catch (error) {
      console.error("Error fetching centros votacion:", error);
      setCentrosVotacion([]);
    }
  };

  const fetchElectores = async () => {
    try {
      const query = new URLSearchParams({
        skip: ((currentElectorPage - 1) * electoresPerPage).toString(),
        limit: electoresPerPage.toString(),
        ...(codigoEstado && { codigo_estado: codigoEstado }),
        ...(codigoMunicipio && { codigo_municipio: codigoMunicipio }),
        ...(codigoParroquia && { codigo_parroquia: codigoParroquia }),
        ...(codigoCentroVotacion && { codigo_centro_votacion: codigoCentroVotacion }),
      }).toString();

      const response = await fetch(`${APIHost}/api/electores/?${query}`);
      const data: Elector[] = await response.json();
      setElectores(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching electores:", error);
      setElectores([]);
    }
  };

  const fetchTotalElectores = async () => {
    try {
      const query = new URLSearchParams({
        ...(codigoEstado && { codigo_estado: codigoEstado }),
        ...(codigoMunicipio && { codigo_municipio: codigoMunicipio }),
        ...(codigoParroquia && { codigo_parroquia: codigoParroquia }),
        ...(codigoCentroVotacion && { codigo_centro_votacion: codigoCentroVotacion }),
      }).toString();

      const response = await fetch(`${APIHost}/total/electores?${query}`);
      const total = await response.json();
      setTotalPages(Math.ceil(total / electoresPerPage));
    } catch (error) {
      console.error("Error fetching total electores:", error);
      setTotalPages(1);
    }
  };

  const fetchElectorDetail = async (numero_cedula: string) => {
    if (!APIHost) return;
    try {
      const response = await fetch(`${APIHost}/api/electores/cedula/${numero_cedula}`);
      const data: Elector = await response.json();
      setSelectedElector(data);
    } catch (error) {
      console.error("Error fetching elector detail:", error);
    }
  };

  const handleEstadoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setCodigoEstado(value === "Seleccione un estado" ? "" : value);
    setCodigoMunicipio("");
    setCodigoParroquia("");
    setCodigoCentroVotacion("");
    setMunicipios([]);
    setParroquias([]);
    setCentrosVotacion([]);
  };

  const handleMunicipioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setCodigoMunicipio(value);
    setCodigoParroquia("");
    setCodigoCentroVotacion("");
    setParroquias([]);
    setCentrosVotacion([]);
  };

  const handleParroquiaChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setCodigoParroquia(value);
    setCodigoCentroVotacion("");
    setCentrosVotacion([]);
  };

  const handleCentroVotacionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setCodigoCentroVotacion(value);
  };

  const handleCedulaSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCedulaSearch(e.target.value);
  };
  const handleCedulaSearch = async () => {
    if (cedulaSearch) {
      try {
        const response = await fetch(`${APIHost}/api/electores/cedula/${cedulaSearch}`);
        if (response.status === 404) {
          setSearchError("Cédula no encontrada");
          setSelectedElector(null);
          setModalIsOpen(false);
          return;
        }
        const data: Elector = await response.json();
        setSelectedElector(data);
        setSearchError("");
        setModalIsOpen(true);
      } catch (error) {
        console.error("Error searching by cedula:", error);
        setSearchError("Error al buscar la cédula");
      }
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const openModal = (numero_cedula: string) => {
    fetchElectorDetail(numero_cedula);
    setModalIsOpen(true);
  };

  const closeModal = () => {
    setModalIsOpen(false);
    setSelectedElector(null);
    setSearchError("");

  };

  const paginate = (pageNumber: number) => {
    if (pageNumber < 1) {
      setCurrentElectorPage(1);
    } else if (pageNumber > totalPages) {
      setCurrentElectorPage(totalPages);
    } else {
      setCurrentElectorPage(pageNumber);
    }
    fetchElectores();
  };

  const initiateDownload = (type: string, format: string) => {
    setDownloadType({ type, format });
    setShowDownloadDialog(true);
  };

  const startSequentialDownload = async () => {
    if (!downloadType) return;
    
    setShowDownloadDialog(false);
    setIsDownloading(true);
    setDownloadProgress(0);
    setCurrentBatch(0);

    try {
      const query = new URLSearchParams();
      if (codigoEstado) query.append('codigo_estado', codigoEstado);
      if (codigoMunicipio && codigoMunicipio !== "") query.append('codigo_municipio', codigoMunicipio);
      if (codigoParroquia && codigoParroquia !== "") query.append('codigo_parroquia', codigoParroquia);
      if (codigoCentroVotacion && codigoCentroVotacion !== "") query.append('codigo_centro_votacion', codigoCentroVotacion);

      const infoResponse = await fetch(`${APIHost}/download/excel/api/electores/info?${query}`);
      const info = await infoResponse.json();
      setTotalBatches(info.num_batches);

      for (let batchNumber = 1; batchNumber <= info.num_batches; batchNumber++) {
        setCurrentBatch(batchNumber);
        setDownloadProgress((batchNumber - 1) / info.num_batches * 100);

        const url = `${APIHost}/download/excel/api/electores/batch/${batchNumber}?${query}`;
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`Error al descargar el lote ${batchNumber}: ${response.statusText}`);
        }

        const blob = await response.blob();
        const filename = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/["']/g, '') || 
                        `electores_parte_${batchNumber}.xlsx.zip`;

        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);

        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      setDownloadProgress(100);
    } catch (error) {
      console.error('Error en la descarga:', error);
      alert('Hubo un error al descargar los archivos. Por favor, inténtelo de nuevo.');
    } finally {
      setIsDownloading(false);
      setCurrentBatch(0);
      setDownloadProgress(0);
    }
  };

  const downloadCentrosPorEstado = async () => {
    if (!codigoEstado) {
      alert('Por favor, seleccione un estado primero');
      return;
    }

    try {
      setIsDownloading(true);
      const response = await fetch(`${APIHost}/download/excel/centros-por-estado/${codigoEstado}`);
      
      if (!response.ok) {
        throw new Error(`Error al descargar los centros: ${response.statusText}`);
      }

      const blob = await response.blob();
      const filename = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/["']/g, '') || 
                      'centros_electorales.xlsx.zip';

      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Error en la descarga:', error);
      alert('Hubo un error al descargar el archivo. Por favor, inténtelo de nuevo.');
    } finally {
      setIsDownloading(false);
    }
  };

  const downloadElectoresPorCentros = async () => {
    if (!codigoEstado) {
      alert('Por favor, seleccione un estado primero');
      return;
    }

    try {
      setIsDownloading(true);
      setDownloadProgress(0);

      // Obtener información sobre la descarga
      const infoResponse = await fetch(`${APIHost}/download/excel/api/electores-por-centros/info/${codigoEstado}`);
      if (!infoResponse.ok) {
        throw new Error(`Error al obtener información de la descarga: ${infoResponse.statusText}`);
      }
      
      const info = await infoResponse.json();
      
      if (!info.centros || !Array.isArray(info.centros)) {
        throw new Error('Formato de respuesta inválido: no se encontraron centros');
      }

      let centrosProcesados = 0;
      const totalCentros = info.centros.length;

      // Procesar cada centro
      for (const centro of info.centros) {
        try {
          const response = await fetch(
            `${APIHost}/download/excel/api/electores-por-centros/${codigoEstado}/${centro.codigo}`
          );

          if (!response.ok) {
            console.error(`Error al descargar centro ${centro.codigo}: ${response.statusText}`);
            continue;
          }

          const blob = await response.blob();
          const filename = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/["']/g, '') || 
                        `centro_${centro.codigo}.xlsx.zip`;

          const downloadUrl = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(downloadUrl);

          centrosProcesados++;
          const progreso = (centrosProcesados / totalCentros) * 100;
          setDownloadProgress(progreso);

          // Pequeña pausa entre descargas
          await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (error) {
          console.error(`Error descargando centro ${centro.codigo}:`, error);
        }
      }

      setDownloadProgress(100);
    } catch (error) {
      console.error('Error en la descarga:', error);
      alert('Hubo un error al descargar los archivos. Por favor, inténtelo de nuevo.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="p-4">
      <h2>Control de Electores</h2>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <label>Estado:</label>
          <select 
            onChange={handleEstadoChange} 
            className="input input-bordered w-full" 
            value={codigoEstado || ""}
          >
            <option value="">Seleccione un estado</option>
            {estados.map(estado => (
              <option key={estado.codigo_estado} value={estado.codigo_estado}>
                {estado.estado}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Municipio:</label>
          <select
            onChange={handleMunicipioChange}
            className="input input-bordered w-full"
            value={codigoMunicipio}
            disabled={!codigoEstado}
          >
            <option value="">Seleccione un municipio</option>
            {municipios.map(municipio => (
              <option key={municipio.codigo_municipio} value={municipio.codigo_municipio}>
                {municipio.municipio}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Parroquia:</label>
          <select
            onChange={handleParroquiaChange}
            className="input input-bordered w-full"
            value={codigoParroquia}
            disabled={!codigoMunicipio}
          >
            <option value="">Seleccione una parroquia</option>
            {parroquias.map(parroquia => (
              <option key={parroquia.codigo_parroquia} value={parroquia.codigo_parroquia}>
                {parroquia.parroquia}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Centro de Votación:</label>
          <select
            onChange={handleCentroVotacionChange}
            className="input input-bordered w-full"
            value={codigoCentroVotacion}
            disabled={!codigoParroquia}
          >
            <option value="">Seleccione un centro de votación</option>
            {centrosVotacion.map(centro => (
              <option key={centro.codificacion_nueva_cv} value={centro.codificacion_nueva_cv}>
                {centro.nombre_cv}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Búsqueda por cédula:</label>
          <input
            type="text"
            value={cedulaSearch}
            onChange={handleCedulaSearchChange}
            className="input input-bordered w-full"
          />
          <button onClick={handleCedulaSearch} className="btn btn-primary w-full mt-2">Buscar</button>
        </div>
        <div>
          <label>Búsqueda general:</label>
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchChange}
            className="input input-bordered w-full"
          />
        </div>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <button 
          onClick={() => initiateDownload('electores', 'excel')} 
          className="btn btn-secondary"
          disabled={isDownloading}
        >
          {isDownloading ? 'Descargando...' : 'Descargar Electores Excel'}
        </button>
        <button 
          onClick={downloadCentrosPorEstado} 
          className="btn btn-primary"
          disabled={!codigoEstado || isDownloading}
        >
          {isDownloading ? 'Descargando...' : 'Descargar Centros del Estado'}
        </button>
        <button
          onClick={downloadElectoresPorCentros}
          disabled={!codigoEstado || isDownloading}
          className={`flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
            !codigoEstado || isDownloading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isDownloading ? (
            <>
              <span className="mr-2">Descargando... {downloadProgress.toFixed(1)}%</span>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            </>
          ) : (
            'Descargar Electores por Centros'
          )}
        </button>
      </div>
      <div className="pagination mb-4 flex justify-center">
        <button onClick={() => paginate(1)} className="btn btn-primary mr-1">{"<<"}</button>
        <button onClick={() => paginate(currentElectorPage - 1)} className="btn btn-primary mr-1">{"<"}</button>
        <span className="btn btn-disabled mr-1">Página {currentElectorPage} de {totalPages}</span>
        <button onClick={() => paginate(currentElectorPage + 1)} className="btn btn-primary mr-1">{">"}</button>
        <button onClick={() => paginate(totalPages)} className="btn btn-primary">{">>"}</button>
      </div>
      <table className="table-auto w-full mb-4">
        <thead>
          <tr>
            <th>Cédula</th>
            <th>Nombre</th>
            <th>Apellido</th>
            <th>Centro de Votación</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {electores.map((elector) => (
            <tr key={elector?.id}>
              <td>{`${elector?.letra_cedula}-${elector?.numero_cedula}`}</td>
              <td>{elector?.p_nombre}</td>
              <td>{elector?.p_apellido}</td>
              <td>{elector?.codigo_centro_votacion}</td>
              <td>
                <button className="btn btn-primary" onClick={() => openModal(elector?.numero_cedula)}>
                  Ver Detalle
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {modalIsOpen && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-button" onClick={closeModal}>×</button>
            <h2>Detalle del Elector</h2>
            {selectedElector && (
              <div>
                <p><strong>ID:</strong> {selectedElector.elector.id}</p>
                <p><strong>Cédula:</strong> {`${selectedElector.elector.letra_cedula}-${selectedElector.elector.numero_cedula}`}</p>
                <p><strong>Nombre:</strong> {`${selectedElector.elector.p_nombre} ${selectedElector.elector.s_nombre}`}</p>
                <p><strong>Apellido:</strong> {`${selectedElector.elector.p_apellido} ${selectedElector.elector.s_apellido}`}</p>
                <p><strong>Sexo:</strong> {selectedElector.elector.sexo}</p>
                <p><strong>Fecha Nacimiento:</strong> {new Date(selectedElector.elector.fecha_nacimiento).toLocaleDateString()}</p>
                <p><strong>Estado:</strong> {selectedElector.geografico.estado}</p>
                <p><strong>Municipio:</strong> {selectedElector.geografico.municipio}</p>
                <p><strong>Parroquia:</strong> {selectedElector.geografico.parroquia}</p>
                <p><strong>Centro de Votación:</strong> {selectedElector.centro_votacion.nombre_cv}</p>
                <p><strong>Dirección Centro de Votación:</strong> {selectedElector.centro_votacion.direccion_cv}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {showDownloadDialog && (
        <div className="modal-overlay" onClick={() => setShowDownloadDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4">Información de Descarga</h3>
            <p className="mb-4">
              Los archivos se descargarán en partes para mayor eficiencia.
              Cada parte se descargará automáticamente tan pronto como esté lista.
              Puede continuar trabajando mientras se completan las descargas.
            </p>
            <div className="flex justify-end gap-2">
              <button 
                className="btn btn-secondary"
                onClick={() => setShowDownloadDialog(false)}
              >
                Cancelar
              </button>
              <button 
                className="btn btn-primary"
                onClick={startSequentialDownload}
              >
                Comenzar descargas
              </button>
            </div>
          </div>
        </div>
      )}

      {isDownloading && (
        <div className="fixed bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg">
          <h4 className="font-bold mb-2">Descargando archivos</h4>
          <div className="mb-2">
            Parte actual: {currentBatch} de {totalBatches}
          </div>
          <div className="w-64 h-2 bg-gray-200 rounded-full">
            <div 
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${downloadProgress}%` }}
            />
          </div>
          <div className="text-sm text-gray-600 mt-1">
            {Math.round(downloadProgress)}% completado
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatComponent;
