#!/bin/bash
for id in {4..103}
do
  curl -X DELETE http://localhost:8000/lineas_telefonicas/$id
  echo "Eliminado ID: $id"
done
