import os
import io
import base64
from flask import Flask, request, jsonify
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/calcular-lote', methods=['POST'])
def calcular_lote():
    try:
        # Verifica se o arquivo foi enviado na requisição (espera o parâmetro 'file')
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado no parâmetro "file"'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome do arquivo vazio'}), 400

        # Lê o conteúdo do DXF enviado
        dxf_bytes = file.read()
        
        # Carrega o DXF usando ezdxf a partir dos bytes
        doc = ezdxf.read(io.BytesIO(dxf_bytes))
        msp = doc.modelspace()

        # Configuração para renderizar o SVG / Matplotlib da geometria planificada
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        
        # Desenha a entidade no backend do matplotlib
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        # Converte a figura gerada para SVG em memória
        svg_io = io.BytesIO()
        fig.savefig(svg_io, format='svg', bbox_inches='tight')
        plt.close(fig)
        
        svg_io.seek(0)
        dxf_svg_content = svg_io.getvalue().decode('utf-8')

        # Exemplo de resposta JSON contendo o dxf_svg e os dados operacionais
        response_data = {
            'dxf_svg': dxf_svg_content,
            'status': 'sucesso',
            'mensagem': 'DXF processado e planificado com sucesso'
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)