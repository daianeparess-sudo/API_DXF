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

        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        def atualizar_limites(x, y):
          nonlocal min_x, min_y, max_x, max_y
          if x < min_x:
            min_x = x
          if x > max_x:
            max_x = x
          if y < min_y:
            min_y = y
          if y > max_y:
            max_y = y

        # Contagem de contornos fechados
        contornos_fechados = 年は 0  # contador base
        segmentos = []

        for entity in msp:
          if entity.dxftype() == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
            total_length += length
            atualizar_limites(start.x, start.y)
            atualizar_limites(end.x, end.y)
            segmentos.append(((round(start.x, 3), round(start.y, 3)), (round(end.x, 3), round(end.y, 3))))
          elif entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            total_length += entity.length()
            pts = list(entity.get_points())
            if len(pts) > 0:
              is_closed = entity.closed
              # Se a polilinhas for fechada por propriedade ou se o último ponto liga ao primeiro
              if is_closed or (len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-3 and abs(pts[0][1] - pts[-1][1]) < 1e-3):
                contornos_fechados += 1
            for point in pts:
              atualizar_limites(point[0], point[1])

        # Heurística simples para contar contornos baseados em polilinhas fechadas + entidades detectadas
        # (Caso queira refinar para linhas soltas formando loops, podemos expandir com lógica de grafos)
        
        largura = (
            round(max_x - min_x, 2)
            if min_x != float("inf") and max_x != float("-inf")
            else 0.0
        )
        altura = (
            round(max_y - min_y, 2)
            if min_y != float("inf") and max_y != float("-inf")
            else 0.0
        )

        comprimento_formatado = round(total_length, 2)
        comprimento_geral_total += comprimento_formatado

        resultados.append({
            "filename": file.filename,
            "total_length": comprimento_formatado,
            "largura": largura,
            "altura": altura,
            "contornos_fechados": max(1, contornos_fechados) # Garante pelo menos 1 contorno principal se houver geometria
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