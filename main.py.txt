import tempfile
import requests
import ezdxf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Estrutura para receber a URL do arquivo DXF vinda do Bubble
class DxfRequest(BaseModel):
    file_url: str

@app.post("/calcular-linhas")
def calcular_comprimento_dxf(data: DxfRequest):
    try:
        # 1. Baixar o arquivo DXF enviado pelo Bubble
        response = requests.get(data.file_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Não foi possível baixar o arquivo DXF.")

        # 2. Salvar temporariamente em disco para o ezdxf ler
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        # 3. Ler o arquivo DXF com a biblioteca ezdxf
        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()

        comprimento_total = 0.0

        # 4. Iterar sobre as entidades geométricas
        for entity in msp:
            # Se for uma linha simples (LINE)
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                # Calcula a distância euclidiana 3D entre os pontos
                comprimento = ((end[0] - start[0])**2 + (end[1] - start[1])**2 + (end[2] - start[2])**2)**0.5
                comprimento_total += comprimento

            # Se for uma polilinha (LWPOLYLINE ou POLYLINE)
            elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                # O ezdxf possui um método embutido para calcular o comprimento de polilinhas
                comprimento_total += entity.length()

        return {
            "success": True,
            "total_length": round(comprimento_total, 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))