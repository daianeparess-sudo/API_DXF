from typing import List
import os
import tempfile
from fastapi import FastAPI, File, HTTPException, UploadFile
import ezdxf

app = FastAPI()


@app.post("/calcular-lote")
async def calcular_lote(files: List[UploadFile] = File(...)):
  resultados = []
  comprimento_geral_total = 0.0

  with tempfile.TemporaryDirectory() as temp_dir:
    for file in files:
      filename = file.filename.lower()
      if not filename.endswith(".dxf"):
        raise HTTPException(
            status_code=400,
            detail=f"O arquivo {file.filename} não é um .dxf válido.",
        )

      file_path = os.path.join(temp_dir, file.filename)
      contents = await file.read()
      with open(file_path, "wb") as f:
        f.write(contents)

      try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        total_length = 0.0

        for entity in msp:
          if entity.dxftype() == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
            total_length += length
          elif entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            total_length += entity.length()

        comprimento_formatado = round(total_length, 2)
        comprimento_geral_total += comprimento_formatado

        resultados.append({
            "filename": file.filename,
            "total_length": comprimento_formatado,
        })
      except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar o arquivo {file.filename}: {str(e)}",
        )

  return {
      "arquivos": resultados,
      "comprimento_geral_total": round(comprimento_geral_total, 2),
      "unit": "unidades",
  }