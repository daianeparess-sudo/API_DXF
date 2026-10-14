from flask import Flask, request, jsonify
import ezdxf
import ezdxf.recover
import io
import os
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/process-dxf', methods=['POST'])
def process_dxf():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    filename = file.filename
    
    # Caminho temporário para salvar o DXF recebido
    temp_path = os.path.join('/tmp', filename) if os.path.exists('/tmp') else filename
    file.save(temp_path)
    
    try:
        # Carrega o DXF de forma segura
        doc, auditor = ezdxf.recover.readfile(temp_path)
        msp = doc.modelspace()
        
        # 1. Cálculo de Largura e Altura (Bounding Box)
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for entity in msp:
            if entity.dxftype() in ('LINE', 'LWPOLYLINE', 'CIRCLE', 'ARC'):
                try:
                    box = entity.bounding_box()
                    min_x = min(min_x, box.extmin.x)
                    min_y = min(min_y, box.extmin.y)
                    max_x = max(max_x, box.extmax.x)
                    max_y = max(max_y, box.extmax.y)
                except:
                    pass
                    
        width = round(max_x - min_x, 2) if max_x > min_x else 0.0
        height = round(max_y - min_y, 2) if max_y > min_y else 0.0

        # 2. Renderização do Desenho Real em formato SVG usando Matplotlib + ezdxf
        fig, ax = plt.subplots(figsize=(6, 6))
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)
        
        ax.axis('off')
        plt.tight_layout()
        
        svg_io = io.BytesIO()
        plt.savefig(svg_io, format='svg', bbox_inches='tight', transparent=True)
        plt.close(fig)
        
        svg_io.seek(0)
        svg_string = svg_io.getvalue().decode('utf-8')
        
        # Remove o arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # 3. Retorna o JSON direto no nível raiz para facilitar a leitura no Bubble
        return jsonify({
            "filename": filename,
            "width": width,
            "height": height,
            "cut_length": 0.0,
            "piercings": 0,
            "dxf_svg": svg_string
        })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)