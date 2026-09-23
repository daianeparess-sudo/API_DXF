from typing import List
import os
import tempfile
import math
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
                circulos_count = 0
                arcos_count = 0

                min_x, min_y = float("inf"), float("inf")
                max_x, max_y = float("-inf"), float("-inf")

                def atualizar_limites(x, y):
                    nonlocal min_x, min_y, max_x, max_y
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y

                for entity in msp:
                    etype = entity.dxftype()
                    
                    if etype == "LINE":
                        start = entity.dxf.start
                        end = entity.dxf.end
                        length = math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2)
                        total_length += length
                        atualizar_limites(start.x, start.y)
                        atualizar_limites(end.x, end.y)
                        
                    elif etype == "CIRCLE":
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        length = 2 * math.pi * radius
                        total_length += length
                        atualizar_limites(center.x - radius, center.y - radius)
                        atualizar_limites(center.x + radius, center.y + radius)
                        circulos_count += 1
                        
                    elif etype == "ARC":
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        start_angle = entity.dxf.start_angle
                        end_angle = entity.dxf.end_angle
                        if end_angle < start_angle:
                            end_angle += 360.0
                        length = radius * math.radians(end_angle - start_angle)
                        total_length += length
                        atualizar_limites(center.x - radius, center.y - radius)
                        atualizar_limites(center.x + radius, center.y + radius)
                        arcos_count += 1
                        
                    elif etype in ("LWPOLYLINE", "POLYLINE"):
                        length = entity.length()
                        total_length += length
                        pts = list(entity.get_points())
                        is_closed = entity.closed
                        if is_closed or (len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 1e-3 and abs(pts[0][1] - pts[-1][1]) < 1e-3):
                            circulos_count += 1
                        for point in pts:
                            atualizar_limites(point[0], point[1])

                contornos_fechados = circulos_count + (arcos_count // 2)

                largura = round(max_x - min_x, 2) if min_x != float("inf") else 0.0
                altura = round(max_y - min_y, 2) if min_y != float("inf") else 0.0

                comprimento_formatado = round(total_length, 2)
                comprimento_geral_total += comprimento_formatado

                resultados.append({
                    "filename": file.filename,
                    "total_length": comprimento_formatado,
                    "largura": largura,
                    "altura": altura,
                    "contornos_fechados": max(1, contornos_fechados)
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