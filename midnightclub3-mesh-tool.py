import os
import sys
import re
import numpy as np
from colorama import init, Fore, Style
import pyvista as pv
from pyvistaqt import BackgroundPlotter  # Para visualização interativa

# Inicializa o Colorama
init(autoreset=True)

# ---------------------------
# Funções de seleção e processamento dos ponteiros e meshes
# ---------------------------
def listar_arquivos(diretorio):
    return [arquivo for arquivo in os.listdir(diretorio)
            if os.path.isfile(os.path.join(diretorio, arquivo))]

def escolher_arquivo():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    arquivos = listar_arquivos(diretorio_atual)
    if not arquivos:
        print(Fore.RED + "Nenhum arquivo encontrado no diretório atual.")
        sys.exit(1)
    print(Fore.CYAN + Style.BRIGHT + "Arquivos disponíveis:")
    for idx, arquivo in enumerate(arquivos, start=1):
        print(f"{idx}. {arquivo}")
    escolha = input(Fore.YELLOW + "Digite o número do arquivo que deseja selecionar: ")
    try:
        indice = int(escolha) - 1
        if indice < 0 or indice >= len(arquivos):
            print(Fore.RED + "Número inválido.")
            sys.exit(1)
        return os.path.join(diretorio_atual, arquivos[indice])
    except ValueError:
        print(Fore.RED + "Entrada inválida. Por favor, digite um número.")
        sys.exit(1)

def processar_arquivo(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'rb') as f:
            dados_offset = f.read(4)
            if len(dados_offset) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para OFFSET.")
                sys.exit(1)
            valor_offset = int.from_bytes(dados_offset, byteorder='little')
            offset = valor_offset - 0x80

            f.seek(0x1A8)
            dados_pointer = f.read(4)
            if len(dados_pointer) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para POINTER_TO_GROUPLIST.")
                sys.exit(1)
            valor_pointer = int.from_bytes(dados_pointer, byteorder='little')
            pointer_to_grouplist = valor_pointer - offset

            if pointer_to_grouplist < 0:
                print(Fore.RED + f"Ponteiro para GROUPLIST negativo: 0x{pointer_to_grouplist:08X}")
                sys.exit(1)
            f.seek(pointer_to_grouplist)
            dados_verificacao = f.read(4)
            if len(dados_verificacao) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para verificação em POINTER_TO_GROUPLIST.")
                sys.exit(1)
            seq_esperada = bytes([0x20, 0x94, 0x7A, 0x00])
            verifica_group = dados_verificacao == seq_esperada

            endereco_pck = pointer_to_grouplist + 0x10
            if endereco_pck < 0:
                print(Fore.RED + f"Endereço para POINTER_TO_PCK_LIST negativo: 0x{endereco_pck:08X}")
                sys.exit(1)
            f.seek(endereco_pck)
            dados_pck = f.read(4)
            if len(dados_pck) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para POINTER_TO_PCK_LIST.")
                sys.exit(1)
            valor_pck = int.from_bytes(dados_pck, byteorder='little')
            pointer_to_pck_list = valor_pck - offset

            if pointer_to_pck_list + 0x02 < 0:
                print(Fore.RED + "PCK_AMOUNT: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(pointer_to_pck_list + 0x02)
            dado_pck_amount = f.read(1)
            if len(dado_pck_amount) < 1:
                print(Fore.RED + "Erro: Não foi possível ler 1 byte para PCK_AMOUNT.")
                sys.exit(1)
            pck_amount = int.from_bytes(dado_pck_amount, byteorder='little')

            if pointer_to_pck_list + 0x04 < 0:
                print(Fore.RED + "Verificação de PCK_LIST: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(pointer_to_pck_list + 0x04)
            dados_verificacao_pck = f.read(4)
            if len(dados_verificacao_pck) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para verificação em POINTER_TO_PCK_LIST + 0x04.")
                sys.exit(1)
            seq_esperada_pck = bytes([0xF0, 0x0E, 0x7A, 0x00])
            verifica_pck = dados_verificacao_pck == seq_esperada_pck

            if pointer_to_pck_list + 0x08 < 0:
                print(Fore.RED + "PCK_MESH_LIST: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(pointer_to_pck_list + 0x08)
            dados_mesh = f.read(4)
            if len(dados_mesh) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para PCK_MESH_LIST.")
                sys.exit(1)
            valor_mesh = int.from_bytes(dados_mesh, byteorder='little')
            pck_mesh_list = valor_mesh - offset

            if pointer_to_pck_list + 0x0C < 0:
                print(Fore.RED + "PCK_NAME_LIST: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(pointer_to_pck_list + 0x0C)
            dados_name = f.read(4)
            if len(dados_name) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para PCK_NAME_LIST.")
                sys.exit(1)
            valor_name = int.from_bytes(dados_name, byteorder='little')
            pck_name_list = valor_name - offset

            pck_index = []
            for i in range(pck_amount):
                addr = pck_mesh_list + i * 4
                if addr < 0:
                    print(Fore.RED + f"PCK_INDEX: endereço negativo na iteração {i}: 0x{addr:08X}. Pulando este item.")
                    continue
                f.seek(addr)
                dado_index = f.read(4)
                if len(dado_index) < 4:
                    print(Fore.RED + f"Erro: O arquivo possui menos de 4 bytes para PCK_INDEX na iteração {i}.")
                    sys.exit(1)
                valor_index = int.from_bytes(dado_index, byteorder='little')
                pck_index.append(valor_index - offset)

            namelist_addresses = []
            for i in range(pck_amount):
                addr_calc = pck_name_list + i * 4
                if addr_calc < 0:
                    print(Fore.RED + f"NAMELIST: endereço negativo na iteração {i}: 0x{addr_calc:08X}.")
                    namelist_addresses.append(None)
                else:
                    f.seek(addr_calc)
                    dado_name_ptr = f.read(4)
                    if len(dado_name_ptr) < 4:
                        print(Fore.RED + f"Erro: O arquivo possui menos de 4 bytes para NAMELIST na iteração {i}.")
                        sys.exit(1)
                    valor_name_ptr = int.from_bytes(dado_name_ptr, byteorder='little')
                    namelist_addresses.append(valor_name_ptr - offset)

            namelist_ascii = []
            for addr in namelist_addresses:
                if addr is None or addr < 0:
                    namelist_ascii.append("<ponteiro inválido>")
                    continue
                f.seek(addr)
                chars = []
                while True:
                    byte = f.read(1)
                    if not byte:
                        break
                    if byte[0] in (0x00, 0xCD):
                        break
                    try:
                        chars.append(byte.decode('ascii'))
                    except UnicodeDecodeError:
                        chars.append('?')
                namelist_ascii.append(''.join(chars))

            return (offset, pointer_to_grouplist, dados_verificacao, verifica_group,
                    pointer_to_pck_list, pck_amount, dados_verificacao_pck, verifica_pck,
                    pck_mesh_list, pck_name_list, pck_index, namelist_ascii)
    except Exception as e:
        print(Fore.RED + f"Erro ao abrir ou processar o arquivo: {e}")
        sys.exit(1)

def processar_grupo(caminho_arquivo, group_addr, offset):
    if group_addr < 0:
        print(Fore.RED + f"Endereço do grupo negativo: 0x{group_addr:08X}")
        sys.exit(1)
    try:
        with open(caminho_arquivo, 'rb') as f:
            f.seek(group_addr)
            dados_group_verify = f.read(4)
            if len(dados_group_verify) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para verificação do grupo.")
                sys.exit(1)
            seq_esperada_grupo = bytes([0x98, 0x0F, 0x7A, 0x00])
            verifica_grupo = dados_group_verify == seq_esperada_grupo

            if group_addr + 0x08 < 0:
                print(Fore.RED + "group_amount: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(group_addr + 0x08)
            dado_group_amount = f.read(1)
            if len(dado_group_amount) < 1:
                print(Fore.RED + "Erro: Não foi possível ler 1 byte para group_amount.")
                sys.exit(1)
            group_amount = int.from_bytes(dado_group_amount, byteorder='little')

            if group_addr + 0x10 < 0:
                print(Fore.RED + "group_pointer: endereço calculado é negativo.")
                sys.exit(1)
            f.seek(group_addr + 0x10)
            dado_group_pointer = f.read(4)
            if len(dado_group_pointer) < 4:
                print(Fore.RED + "Erro: O arquivo possui menos de 4 bytes para group_pointer.")
                sys.exit(1)
            valor_group_pointer = int.from_bytes(dado_group_pointer, byteorder='little')
            group_pointer = valor_group_pointer - offset

            return verifica_grupo, group_amount, group_pointer
    except Exception as e:
        print(Fore.RED + f"Erro ao processar o grupo: {e}")
        sys.exit(1)

def processar_meshgroup(caminho_arquivo, group_pointer, group_amount, offset):
    meshgroup = []
    try:
        with open(caminho_arquivo, 'rb') as f:
            for i in range(group_amount):
                addr = group_pointer + i * 8
                if addr < 0:
                    print(Fore.RED + f"Meshgroup: endereço negativo na iteração {i}: 0x{addr:08X}. Pulando este item.")
                    continue
                f.seek(addr)
                dado_mesh = f.read(4)
                if len(dado_mesh) < 4:
                    print(Fore.RED + f"Erro: O arquivo possui menos de 4 bytes para meshgroup na iteração {i}.")
                    sys.exit(1)
                valor_mesh = int.from_bytes(dado_mesh, byteorder='little')
                meshgroup.append(valor_mesh - offset)
        return meshgroup
    except Exception as e:
        print(Fore.RED + f"Erro ao processar meshgroup: {e}")
        sys.exit(1)

def processar_mesh_entries(caminho_arquivo, meshgroup, offset):
    resultados = []
    try:
        with open(caminho_arquivo, 'rb') as f:
            for idx, addr in enumerate(meshgroup):
                if addr < 0:
                    print(Fore.RED + f"Mesh entry {idx}: endereço inválido (negativo). Pulando.")
                    continue
                f.seek(addr)
                dado_start = f.read(4)
                if len(dado_start) < 4:
                    print(Fore.RED + f"Mesh entry {idx}: não foi possível ler 4 bytes para mesh_start.")
                    continue
                mesh_start = int.from_bytes(dado_start, 'little') - offset

                dado_size = f.read(2)
                if len(dado_size) < 2:
                    print(Fore.RED + f"Mesh entry {idx}: não foi possível ler 2 bytes para mesh_size.")
                    continue
                mesh_size = int.from_bytes(dado_size, 'little') * 0x10

                dado_vtx = f.read(2)
                if len(dado_vtx) < 2:
                    print(Fore.RED + f"Mesh entry {idx}: não foi possível ler 2 bytes para mesh_vtx_total.")
                    continue
                mesh_vtx_total = int.from_bytes(dado_vtx, 'little')

                mesh_end = mesh_start + mesh_size

                resultados.append({
                    'mesh_start': mesh_start,
                    'mesh_size': mesh_size,
                    'mesh_vtx_total': mesh_vtx_total,
                    'mesh_end': mesh_end
                })
        return resultados
    except Exception as e:
        print(Fore.RED + f"Erro ao processar mesh entries: {e}")
        sys.exit(1)

def processar_mesh_data(caminho_arquivo, mesh_start, mesh_end, offset):
    try:
        with open(caminho_arquivo, 'rb') as f:
            f.seek(mesh_start)
            chunk = f.read(mesh_end - mesh_start)
        resultado = {
            'vertices1_groups': [],
            'vertices2_groups': [],
            'uvs1_groups': [],
            'uvs2_groups': [],
            'fflags1_groups': [],
            'fflags2_groups': []
        }
        pat_vert1 = re.compile(b'\xEE\x00([\x00-\x2A])\x69')
        for m in pat_vert1.finditer(chunk):
            cnt = m.group(1)[0]
            st = m.end()
            verts = []
            for i in range(cnt):
                s = st + i * 6
                e = s + 6
                if e > len(chunk): break
                data = chunk[s:e]
                x = int.from_bytes(data[0:2], 'little', signed=True)
                y = int.from_bytes(data[2:4], 'little', signed=True)
                z = int.from_bytes(data[4:6], 'little', signed=True)
                verts.append((x, y, z))
            resultado['vertices1_groups'].append({'count': cnt, 'vertices': verts})
        
        pat_vert2 = re.compile(b'\x1B\x02([\x00-\x2A])\x69')
        for m in pat_vert2.finditer(chunk):
            cnt = m.group(1)[0]
            st = m.end()
            verts = []
            for i in range(cnt):
                s = st + i * 6
                e = s + 6
                if e > len(chunk): break
                data = chunk[s:e]
                x = int.from_bytes(data[0:2], 'little', signed=True)
                y = int.from_bytes(data[2:4], 'little', signed=True)
                z = int.from_bytes(data[4:6], 'little', signed=True)
                verts.append((x, y, z))
            resultado['vertices2_groups'].append({'count': cnt, 'vertices': verts})
        
        pat_uv1 = re.compile(b'\xC4\x00([\x00-\x2A])([\x65\x66])')
        for m in pat_uv1.finditer(chunk):
            cnt = m.group(1)[0]
            uv_type = m.group(2)[0]
            st = m.end()
            uvs = []
            if uv_type == 0x65:
                for i in range(cnt):
                    s = st + i * 4
                    e = s + 4
                    if e > len(chunk): break
                    data = chunk[s:e]
                    u = int.from_bytes(data[0:2], 'little', signed=True)
                    v = int.from_bytes(data[2:4], 'little', signed=True)
                    uvs.append((u, v))
            resultado['uvs1_groups'].append({'count': cnt, 'uv_type': uv_type, 'uvs': uvs})
        
        pat_uv2 = re.compile(b'\xF1\x01([\x00-\x2A])([\x65\x66])')
        for m in pat_uv2.finditer(chunk):
            cnt = m.group(1)[0]
            uv_type = m.group(2)[0]
            st = m.end()
            uvs = []
            if uv_type == 0x65:
                for i in range(cnt):
                    s = st + i * 4
                    e = s + 4
                    if e > len(chunk): break
                    data = chunk[s:e]
                    u = int.from_bytes(data[0:2], 'little', signed=True)
                    v = int.from_bytes(data[2:4], 'little', signed=True)
                    uvs.append((u, v))
            resultado['uvs2_groups'].append({'count': cnt, 'uv_type': uv_type, 'uvs': uvs})
        
        pat_fflags1 = re.compile(b'\x9A\x00([\x00-\x2A])\x6A')
        for m in pat_fflags1.finditer(chunk):
            raw = m.group(1)[0]
            cnt_flags = raw - 2 if raw >= 2 else 0
            pos = m.end() + 6
            flags = []
            for i in range(cnt_flags):
                if pos >= len(chunk): break
                flags.append(chunk[pos])
                pos += 3
            resultado['fflags1_groups'].append({'count': raw, 'flags': [("ativado" if v % 2 == 0 else "desativado") for v in flags]})
        
        pat_fflags2 = re.compile(b'\xC7\x01([\x00-\x2A])\x6A')
        for m in pat_fflags2.finditer(chunk):
            raw = m.group(1)[0]
            cnt_flags = raw - 2 if raw >= 2 else 0
            pos = m.end() + 6
            flags = []
            for i in range(cnt_flags):
                if pos >= len(chunk): break
                flags.append(chunk[pos])
                pos += 3
            resultado['fflags2_groups'].append({'count': raw, 'flags': [("ativado" if v % 2 == 0 else "desativado") for v in flags]})
        
        return resultado
    except Exception as e:
        print(Fore.RED + f"Erro ao processar mesh data: {e}")
        sys.exit(1)

def gerar_faces(vertices, flags):
    num_vertices = len(vertices)
    num_faces = max(num_vertices - 2, 0)
    faces = []
    face_status = []
    for i in range(num_faces):
        face = [3, i, i+1, i+2]
        faces.append(face)
        if i < len(flags):
            face_status.append(1 if flags[i] == "ativado" else 0)
        else:
            face_status.append(1)
    return faces, face_status

def sanitizar_nome(nome):
    return re.sub(r'[\\/*?:"<>|]', "_", nome).strip()

def scale_vertices(vertices, scale=256.0):
    return [(x/scale, y/scale, z/scale) for (x, y, z) in vertices]

def scale_uvs(uvs, scale=256.0):
    return [(u/scale, v/scale) for (u, v) in uvs]

# ---------------------------
# Função para visualizar globalmente e exportar OBJ com smooth shading e cores para cada mesh
# ---------------------------
def visualizar_global(global_vertices, global_faces, global_uvs, global_face_colors, export_name=None):
    poly = pv.PolyData(np.array(global_vertices), np.hstack(global_faces))
    if global_uvs:
        poly.active_texture_coordinates = np.array(global_uvs)
    poly.compute_normals(cell_normals=False, point_normals=True,
                         auto_orient_normals=True, inplace=True)
    pl = pv.Plotter(title="Visualização Global de Meshes")
    # Removido show_edges para desativar as bordas
    pl.add_mesh(poly, scalars=np.array(global_face_colors), cmap="tab20", smooth_shading=True)
    pl.add_axes()
    pl.show()
    if export_name:
        try:
            poly.save(export_name)
            print(Fore.GREEN + f"Mesh exportado com sucesso para '{export_name}'.")
        except Exception as e:
            print(Fore.RED + f"Erro ao exportar OBJ: {e}")

# ---------------------------
# Função para exportar individualmente OBJ para cada grupo de cada mesh
# ---------------------------
def exportar_individualmente(caminho, mesh_entries, offset, export_dir, scale=False):
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    count_export = 0
    for me_idx, entry in enumerate(mesh_entries, start=1):
        ms = entry['mesh_start']
        me = entry['mesh_end']
        dados_internos = processar_mesh_data(caminho, ms, me, offset)
        # Cada mesh entry terá sua própria cor (usando seu índice)
        for padrao, key_verts, key_uvs, key_fflags in [(1, 'vertices1_groups', 'uvs1_groups', 'fflags1_groups'),
                                                       (2, 'vertices2_groups', 'uvs2_groups', 'fflags2_groups')]:
            verts_groups = dados_internos.get(key_verts, [])
            uv_groups = dados_internos.get(key_uvs, [])
            fflags_groups = dados_internos.get(key_fflags, [])
            for gi, group in enumerate(verts_groups, start=1):
                verts = group['vertices']
                if scale:
                    verts = scale_vertices(verts)
                if gi - 1 < len(uv_groups):
                    uvs = uv_groups[gi - 1]['uvs']
                    if scale:
                        uvs = scale_uvs(uvs)
                    if len(uvs) != len(verts):
                        uvs = uvs + [(0,0)]*(len(verts)-len(uvs))
                else:
                    uvs = [(0,0)] * len(verts)
                if gi - 1 < len(fflags_groups):
                    flags = fflags_groups[gi - 1]['flags']
                else:
                    flags = ["ativado"] * max(len(verts)-2, 0)
                faces, face_status = gerar_faces(verts, flags)
                active_faces = []
                for i, face in enumerate(faces):
                    if face_status[i] == 1:
                        active_faces.append(face)
                if not active_faces:
                    continue
                poly = pv.PolyData(np.array(verts), np.hstack(active_faces))
                poly.active_texture_coordinates = np.array(uvs)
                poly.compute_normals(cell_normals=False, point_normals=True,
                                     auto_orient_normals=True, inplace=True)
                filename = os.path.join(export_dir, f"Mesh{me_idx}_Padrao{padrao}_Grupo{gi}.obj")
                try:
                    poly.save(filename)
                    print(Fore.GREEN + f"Exportado: {filename}")
                    count_export += 1
                except Exception as e:
                    print(Fore.RED + f"Erro ao exportar {filename}: {e}")
    if count_export == 0:
        print(Fore.RED + "Nenhum OBJ individual foi gerado.")

# ---------------------------
# Função principal
# ---------------------------
def main():
    print(Fore.CYAN + Style.BRIGHT + "Selecione o arquivo para processamento:")
    caminho = escolher_arquivo()
    (offset, pointer_group, dados_group, verifica_group,
     pointer_to_pck_list, pck_amount, dados_verificacao_pck, verifica_pck,
     pck_mesh_list, pck_name_list, pck_index, namelist_ascii) = processar_arquivo(caminho)
    
    print(Fore.CYAN + Style.BRIGHT + "\nLista Agrupada (PCK_INDEX com NAMELIST):")
    for i, (idx_val, name_str) in enumerate(zip(pck_index, namelist_ascii), start=1):
        print(Fore.YELLOW + Style.BRIGHT + f"{i}. {name_str} - PCK_INDEX: 0x{idx_val:08X}")
    
    escolha = input(Fore.YELLOW + "\nDigite o número do grupo que deseja selecionar: ")
    try:
        grupo_selecionado = int(escolha)
        if grupo_selecionado < 1 or grupo_selecionado > len(pck_index):
            print(Fore.RED + "Número de grupo inválido.")
            sys.exit(1)
    except ValueError:
        print(Fore.RED + "Entrada inválida. Por favor, digite um número.")
        sys.exit(1)
    
    nome_grupo = namelist_ascii[grupo_selecionado - 1]
    nome_grupo_sanitizado = sanitizar_nome(nome_grupo) if nome_grupo != "<ponteiro inválido>" else "grupo_sem_nome"
    export_name_global = f"{nome_grupo_sanitizado}.obj"
    
    group_addr = pck_index[grupo_selecionado - 1]
    verifica_grupo_sel, group_amount, group_pointer = processar_grupo(caminho, group_addr, offset)
    group_verify_str = "98 0F 7A 00" if verifica_grupo_sel else "Sequência diferente de 98 0F 7A 00"
    print(Fore.GREEN + Style.BRIGHT + "\nGrupo Selecionado:")
    print(Fore.GREEN + Style.BRIGHT + f"Endereço do Grupo: 0x{group_addr:08X}")
    print(Fore.GREEN + Style.BRIGHT + f"Verificação do Grupo: {group_verify_str}")
    print(Fore.GREEN + Style.BRIGHT + f"Group Amount: {group_amount}")
    print(Fore.GREEN + Style.BRIGHT + f"Group Pointer: 0x{group_pointer:08X}")
    
    meshgroup = processar_meshgroup(caminho, group_pointer, group_amount, offset)
    meshgroup_str = [f"0x{valor:08X}" for valor in meshgroup]
    print(Fore.GREEN + Style.BRIGHT + f"\nMeshgroup: {meshgroup_str}")
    
    mesh_entries = processar_mesh_entries(caminho, meshgroup, offset)
    print(Fore.CYAN + Style.BRIGHT + "\nDetalhes das Entradas de Mesh:")
    for idx, entry in enumerate(mesh_entries, start=1):
        print(Fore.YELLOW + Style.BRIGHT +
              f"{idx}. Mesh Start: 0x{entry['mesh_start']:08X} | "
              f"Mesh Size: 0x{entry['mesh_size']:04X} | "
              f"Mesh VTX Total: {entry['mesh_vtx_total']} | "
              f"Mesh End: 0x{entry['mesh_end']:08X}")
    
    print(Fore.CYAN + Style.BRIGHT + "\nOpções:")
    print("1. Gerar OBJ global (todas as meshes combinadas) - sem escala")
    print("2. Gerar OBJ individualmente (cada grupo em um arquivo separado) - sem escala")
    print("3. Não gerar OBJ")
    print("4. Apenas visualizar em 3D (sem exportar OBJ)")
    print("5. Gerar OBJ global com vértices e UVs divididos por 256")
    print("6. Gerar OBJ individualmente com vértices e UVs divididos por 256")
    opcao = input(Fore.YELLOW + "Digite sua opção (1, 2, 3, 4, 5 ou 6): ")
    
    # Para visualização global, vamos criar um vetor de cores, onde cada mesh entry recebe uma cor única.
    global_face_colors = []
    
    if opcao == "1":
        global_vertices = []
        global_uvs = []
        global_faces = []
        vert_offset = 0
        # Para cada mesh entry, use seu índice (iniciando em 1) para a cor
        for m_idx, entry in enumerate(mesh_entries, start=1):
            mesh_color = m_idx  # Cor atribuída a toda a mesh entry
            ms = entry['mesh_start']
            me = entry['mesh_end']
            dados_internos = processar_mesh_data(caminho, ms, me, offset)
            for padrao, key_verts, key_uvs, key_fflags in [(1, 'vertices1_groups', 'uvs1_groups', 'fflags1_groups'),
                                                           (2, 'vertices2_groups', 'uvs2_groups', 'fflags2_groups')]:
                verts_groups = dados_internos.get(key_verts, [])
                uv_groups = dados_internos.get(key_uvs, [])
                fflags_groups = dados_internos.get(key_fflags, [])
                for gi, group in enumerate(verts_groups):
                    verts = group['vertices']
                    if gi < len(uv_groups):
                        uvs = uv_groups[gi]['uvs']
                        if len(uvs) != len(verts):
                            uvs = uvs + [(0,0)]*(len(verts)-len(uvs))
                    else:
                        uvs = [(0,0)] * len(verts)
                    if gi < len(fflags_groups):
                        flags = fflags_groups[gi]['flags']
                    else:
                        flags = ["ativado"] * max(len(verts)-2, 0)
                    faces, face_status = gerar_faces(verts, flags)
                    for i, face in enumerate(faces):
                        if face_status[i] == 1:
                            global_faces.append([face[0], face[1] + vert_offset,
                                                   face[2] + vert_offset, face[3] + vert_offset])
                            global_face_colors.append(mesh_color)
                    global_vertices.extend(verts)
                    global_uvs.extend(uvs)
                    vert_offset = len(global_vertices)
        if not global_vertices or not global_faces:
            print(Fore.RED + "Nenhuma face ativa encontrada para exportação.")
            sys.exit(1)
        export_name = export_name_global
        global_faces_flat = np.hstack(global_faces)
        poly = pv.PolyData(np.array(global_vertices), global_faces_flat)
        if global_uvs:
            poly.active_texture_coordinates = np.array(global_uvs)
        poly.compute_normals(cell_normals=False, point_normals=True,
                             auto_orient_normals=True, inplace=True)
        visualizar_global(global_vertices, global_faces, global_uvs, global_face_colors, export_name)
    elif opcao == "2":
        export_dir = f"{nome_grupo_sanitizado}_individual_objs"
        exportar_individualmente(caminho, mesh_entries, offset, export_dir, scale=False)
    elif opcao == "3":
        print(Fore.CYAN + "Nenhum OBJ foi gerado.")
    elif opcao == "4":
        global_vertices = []
        global_uvs = []
        global_faces = []
        vert_offset = 0
        global_face_colors = []
        for m_idx, entry in enumerate(mesh_entries, start=1):
            mesh_color = m_idx
            ms = entry['mesh_start']
            me = entry['mesh_end']
            dados_internos = processar_mesh_data(caminho, ms, me, offset)
            for padrao, key_verts, key_uvs, key_fflags in [(1, 'vertices1_groups', 'uvs1_groups', 'fflags1_groups'),
                                                           (2, 'vertices2_groups', 'uvs2_groups', 'fflags2_groups')]:
                verts_groups = dados_internos.get(key_verts, [])
                uv_groups = dados_internos.get(key_uvs, [])
                fflags_groups = dados_internos.get(key_fflags, [])
                for gi, group in enumerate(verts_groups):
                    verts = group['vertices']
                    if gi < len(uv_groups):
                        uvs = uv_groups[gi]['uvs']
                        if len(uvs) != len(verts):
                            uvs = uvs + [(0,0)]*(len(verts)-len(uvs))
                    else:
                        uvs = [(0,0)] * len(verts)
                    if gi < len(fflags_groups):
                        flags = fflags_groups[gi]['flags']
                    else:
                        flags = ["ativado"] * max(len(verts)-2, 0)
                    faces, face_status = gerar_faces(verts, flags)
                    for i, face in enumerate(faces):
                        if face_status[i] == 1:
                            global_faces.append([face[0], face[1] + vert_offset,
                                                   face[2] + vert_offset, face[3] + vert_offset])
                            global_face_colors.append(mesh_color)
                    global_vertices.extend(verts)
                    global_uvs.extend(uvs)
                    vert_offset = len(global_vertices)
        if not global_vertices or not global_faces:
            print(Fore.RED + "Nenhuma face ativa encontrada para visualização.")
            sys.exit(1)
        global_faces_flat = np.hstack(global_faces)
        poly = pv.PolyData(np.array(global_vertices), global_faces_flat)
        if global_uvs:
            poly.active_texture_coordinates = np.array(global_uvs)
        poly.compute_normals(cell_normals=False, point_normals=True,
                             auto_orient_normals=True, inplace=True)
        visualizar_global(global_vertices, global_faces, global_uvs, global_face_colors, None)
    elif opcao == "5":
        global_vertices = []
        global_uvs = []
        global_faces = []
        vert_offset = 0
        global_face_colors = []
        for m_idx, entry in enumerate(mesh_entries, start=1):
            mesh_color = m_idx
            ms = entry['mesh_start']
            me = entry['mesh_end']
            dados_internos = processar_mesh_data(caminho, ms, me, offset)
            for padrao, key_verts, key_uvs, key_fflags in [(1, 'vertices1_groups', 'uvs1_groups', 'fflags1_groups'),
                                                           (2, 'vertices2_groups', 'uvs2_groups', 'fflags2_groups')]:
                verts_groups = dados_internos.get(key_verts, [])
                uv_groups = dados_internos.get(key_uvs, [])
                fflags_groups = dados_internos.get(key_fflags, [])
                for gi, group in enumerate(verts_groups):
                    mesh_color_inner = mesh_color  # usa a mesma cor para toda a mesh
                    verts = group['vertices']
                    verts = scale_vertices(verts)
                    if gi < len(uv_groups):
                        uvs = uv_groups[gi]['uvs']
                        uvs = scale_uvs(uvs)
                        if len(uvs) != len(verts):
                            uvs = uvs + [(0,0)]*(len(verts)-len(uvs))
                    else:
                        uvs = [(0,0)] * len(verts)
                    if gi < len(fflags_groups):
                        flags = fflags_groups[gi]['flags']
                    else:
                        flags = ["ativado"] * max(len(verts)-2, 0)
                    faces, face_status = gerar_faces(verts, flags)
                    for i, face in enumerate(faces):
                        if face_status[i] == 1:
                            global_faces.append([face[0], face[1] + vert_offset,
                                                   face[2] + vert_offset, face[3] + vert_offset])
                            global_face_colors.append(mesh_color_inner)
                    global_vertices.extend(verts)
                    global_uvs.extend(uvs)
                    vert_offset = len(global_vertices)
        if not global_vertices or not global_faces:
            print(Fore.RED + "Nenhuma face ativa encontrada para exportação.")
            sys.exit(1)
        export_name = f"{nome_grupo_sanitizado}_scaled.obj"
        global_faces_flat = np.hstack(global_faces)
        poly = pv.PolyData(np.array(global_vertices), global_faces_flat)
        if global_uvs:
            poly.active_texture_coordinates = np.array(global_uvs)
        poly.compute_normals(cell_normals=False, point_normals=True,
                             auto_orient_normals=True, inplace=True)
        visualizar_global(global_vertices, global_faces, global_uvs, global_face_colors, export_name)
    elif opcao == "6":
        export_dir = f"{nome_grupo_sanitizado}_individual_objs_scaled"
        exportar_individualmente(caminho, mesh_entries, offset, export_dir, scale=True)
    else:
        print(Fore.RED + "Opção inválida.")

if __name__ == "__main__":
    main()
