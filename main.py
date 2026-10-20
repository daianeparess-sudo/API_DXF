import os
import io
import tempfile
import math
from flask import Flask, request, jsonify
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
from ezdxf.addons.drawing.properties import LayoutProperties

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

        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        doc = ezdxf.readfile(temp_path)
        msp = doc.modelspace()

        comprimento_vermelho = 0.0
        comprimento_outras = 0.0
        comprimento_geral = 0.0

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        def atualizar_limites(x, y):
            nonlocal min_x, min_y, max_x, max_y
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y

        linhas_count = 0
        arcos_count = 0
        circulos_count = 0
        polilinhas_count = 0

        for entity in msp:
            etype = entity.dxftype()
            color = entity.dxf.color if hasattr(entity.dxf, 'color') else 7
            comprimento_entidade = 0.0

            if etype == 'LINE':
                linhas_count += 1
                start = entity.dxf.start
                end = entity.dxf.end
                comprimento_entidade = ((end.x - start.x)**2 + (end.y - start.y)**2)**0.5
                atualizar_limites(start.x, start.y)
                atualizar_limites(end.x, end.y)

            elif etype in ('LWPOLYLINE', 'POLYLINE'):
                polilinhas_count += 1
                try:
                    comprimento_entidade = entity.length
                except:
                    comprimento_entidade = 0.0
                for point in entity.get_points():
                    atualizar_limites(point[0], point[1])

            elif etype == 'ARC':
                arcos_count += 1
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                sweep = abs(end_angle - start_angle)
                if sweep > 360: sweep = 360
                comprimento_entidade = 2 * math.pi * radius * (sweep / 360.0)
                atualizar_limites(entity.dxf.center.x - radius, entity.dxf.center.y - radius)
                atualizar_limites(entity.dxf.center.x + radius, entity.dxf.center.y + radius)

            elif etype == 'CIRCLE':
                circulos_count += 1
                radius = entity.dxf.radius
                comprimento_entidade = 2 * math.pi * radius
                atualizar_limites(entity.dxf.center.x - radius, entity.dxf.center.y - radius)
                atualizar_limites(entity.dxf.center.x + radius, entity.dxf.center.y + radius)

            if color == 1:
                comprimento_vermelho += comprimento_entidade
            else:
                comprimento_outras += comprimento_entidade

            comprimento_geral += comprimento_entidade

        if min_x != float('inf'):
            largura = max_x - min_x
            altura = max_y - min_y
        else:
            largura = 0.0
            altura = 0.0

        contornos_calculados = 1
        if arcos_count > 0:
            contornos_calculados += int(arcos_count / 2)
        elif circulos_count > 0:
            contornos_calculados += circulos_count

        # Renderização do SVG com fundo branco e forçando cor preta para os traços
        fig = plt.figure(figsize=(10, 10), facecolor='white')
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor('white')
        ax.axis('off')

        ctx = RenderContext(doc)
        # Configurar cores padrão da camada para preto forte
        ctx.set_current_layout_properties(LayoutProperties(background_color='#ffffff'))
        
        out = MatplotlibBackend(ax)
        frontend = Frontend(ctx, out)
        
        # Sobrescrever a cor de exibição de todas as entidades para preto (#000000)
        class BlackFrontend(Frontend):
            def get_entity_color(self, entity, corrected_color=True):
                return '#000000'

        # Usar o frontend com traços pretos
        out_backend = MatplotlibBackend(ax)
        Frontend(ctx, out_backend).draw_layout(msp, finalize=True)
        
        # Forçar linhas do plot para preto caso tenham ficado cinzentas
        for line in ax.get_lines():
            line.set_color('#000000')
        for coll in ax.collections:
            coll.set_color('#000000')

        svg_io = io.BytesIO()
        fig.savefig(svg_io, format='svg', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        
        svg_io.seek(0)
        dxf_svg_content = svg_io.getvalue().decode('utf-8')

        response_data = {
            "dxf_svg": dxf_svg_content,
            "nome_arquivo": file.filename,
            "comprimento_total": round(comprimento_geral, 2),
            "largura": round(largura, 2),
            "altura": round(altura, 2),
            "comprimento_linhas_vermelhas": round(comprimento_vermelho, 2),
            "comprimento_linhas_outras_cores": round(comprimento_outras, 2),
            "contornos_fechados": contornos_calculados,
            "total_entidades": len(msp),
            "linhas": linhas_count,
            "arcos": arcos_count,
            "circulos": circulos_count,
            "polilinhas": polilinhas_count,
            "status": "sucesso",
            "mensagem": "DXF planificado e calculado com sucesso"
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