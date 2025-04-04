export const detectHost = async (): Promise<string> => {
  // Utiliza la URL desde el archivo .env, o usa un valor predeterminado si no está disponible
  const apiUrl = process.env.HOST || "http://localhost:8000";
  // Eliminar cualquier barra diagonal al final de la URL
  return apiUrl.replace(/\/+$/, '');
};

