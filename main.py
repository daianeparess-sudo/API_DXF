import os
import io
import tempfile
import base64
from flask import Flask, request, jsonify
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/calcular-lote', methods=['POST'])
def calcular_lote():
    temp_path = None
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado no parâmetro "file"'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nome do arquivo vazio'}), 400

        # Grava num ficheiro temporário para leitura 100% segura pelo ezdxf
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()

        # Análise básica de entidades para métricas (perímetro, contagem, etc.)
        total_entidades = len(msp)
        linhas = len(msp.query('LINE'))
        arcos = len(msp.query('ARC'))
        circulos = len(msp.query('CIRCLE'))
        polilinhas = len(msp.query('LWPOLYLINE'))

        # Renderização da vista planificada para SVG utilizando o matplotlib
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        svg_io = io.BytesIO()
        fig.savefig(svg_io, format='svg', bbox_inches='tight')
        plt.close(fig)
        
        svg_io.seek(0)
        dxf_svg_content = svg_io.getvalue().decode('utf-8')

        # Resposta completa contendo o SVG e todas as propriedades operacionais
        response_data = {
            'dxf_svg': dxf_svg_content,
            'nome_arquivo': file.filename,
            'total_entidades': total_entidades,
            'linhas': linhas,
            'arcos': arcos,
            'circulos': circulos,
            'polilinhas': polilinhas,
            'status': 'sucesso',
            'mensagem': 'DXF processado, planificado e calculado com sucesso'
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)