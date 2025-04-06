import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import shutil
from datetime import datetime
import tempfile

class ImageProcessor:
    """Clase para procesar imágenes: convertir y redimensionar"""
    
    # Dimensiones predefinidas según los requisitos de OPL Manager
    DIMENSIONS = {
        "caratula": (140, 200),
        "borde": (18, 240),
        "contracaratula": (242, 344),
        "captura": (250, 168),
        "fondo": (640, 480),
        "disco": (128, 128),
        "logo": (300, 125)
    }
    
    # Formatos de entrada soportados
    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.gif']
    
    @staticmethod
    def is_supported_format(file_path):
        """Verifica si el formato del archivo es soportado"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in ImageProcessor.SUPPORTED_FORMATS
    
    @staticmethod
    def convert_resize_image(input_path, output_path, image_type, maintain_aspect=True):
        """Convierte y redimensiona una imagen según el tipo especificado"""
        try:
            # Abrir la imagen
            img = Image.open(input_path)
            
            # Convertir a RGB si es necesario (para formatos como RGBA)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Obtener dimensiones objetivo
            target_width, target_height = ImageProcessor.DIMENSIONS.get(image_type, (0, 0))
            
            if target_width == 0 or target_height == 0:
                raise ValueError(f"Tipo de imagen no válido: {image_type}")
            
            # Redimensionar manteniendo la relación de aspecto si se solicita
            if maintain_aspect:
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                target_ratio = target_width / target_height
                
                if aspect_ratio > target_ratio:
                    # Imagen más ancha que el objetivo
                    new_width = target_width
                    new_height = int(new_width / aspect_ratio)
                else:
                    # Imagen más alta que el objetivo
                    new_height = target_height
                    new_width = int(new_height * aspect_ratio)
                
                # Crear una nueva imagen con fondo negro del tamaño objetivo
                new_img = Image.new('RGB', (target_width, target_height), (0, 0, 0))
                
                # Redimensionar la imagen original
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Calcular posición para centrar
                left = (target_width - new_width) // 2
                top = (target_height - new_height) // 2
                
                # Pegar la imagen redimensionada en el centro
                new_img.paste(resized_img, (left, top))
                img = new_img
            else:
                # Redimensionar sin mantener la relación de aspecto
                img = img.resize((target_width, target_height), Image.LANCZOS)
            
            # Guardar como PNG
            img.save(output_path, 'PNG')
            return True, output_path
        
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def batch_process(input_files, output_dir, image_type, maintain_aspect=True, callback=None):
        """Procesa un lote de imágenes"""
        results = []
        
        for input_file in input_files:
            if not ImageProcessor.is_supported_format(input_file):
                results.append((input_file, False, "Formato no soportado"))
                continue
            
            # Generar nombre de archivo de salida
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_name = f"{base_name}_{image_type}.png"
            output_path = os.path.join(output_dir, output_name)
            
            # Verificar si el archivo ya existe
            counter = 1
            while os.path.exists(output_path):
                output_name = f"{base_name}_{image_type}_{counter}.png"
                output_path = os.path.join(output_dir, output_name)
                counter += 1
            
            # Procesar la imagen
            success, message = ImageProcessor.convert_resize_image(
                input_file, output_path, image_type, maintain_aspect
            )
            
            results.append((input_file, success, message if not success else output_path))
            
            # Llamar al callback si existe
            if callback:
                callback(input_file, success, message if not success else output_path)
        
        return results


class OPLImageConverterApp:
    """Aplicación principal con interfaz gráfica"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OPL Manager - Conversor de Imágenes")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Variables
        self.input_files = []
        self.output_dir = os.path.join(os.path.expanduser("~"), "OPL_Images")
        self.image_type = tk.StringVar(value="caratula")
        self.maintain_aspect = tk.BooleanVar(value=True)
        self.current_preview_index = 0
        self.preview_original = None
        self.preview_processed = None
        self.drag_message = "Arrastre su archivo de imagen original aquí para que sea procesado para el OPL-Manager\n\nConvierta cualquier imagen (.jpg, .jpeg, .png, .bmp, .webp, etc.) a formato .PNG compatible con OPL MANAGER"
        
        # Asegurar que existe el directorio de salida
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Crear la interfaz
        self._create_ui()
        
        # Inicializar el historial
        self.history = []
        self._load_history()
    
    def _create_ui(self):
        """Crea la interfaz de usuario"""
        # Frame principal con dos columnas
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Columna izquierda: Controles
        control_frame = ttk.LabelFrame(main_frame, text="Controles", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        # Sección de selección de archivos
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Seleccionar Archivos", 
                  command=self._select_files).pack(fill=tk.X, pady=2)
        
        ttk.Button(file_frame, text="Seleccionar Carpeta", 
                  command=self._select_folder).pack(fill=tk.X, pady=2)
        
        # Contador de archivos seleccionados
        self.files_label = ttk.Label(file_frame, text="0 archivos seleccionados")
        self.files_label.pack(fill=tk.X, pady=5)
        
        # Sección de tipo de imagen
        type_frame = ttk.LabelFrame(control_frame, text="Tipo de Imagen", padding=5)
        type_frame.pack(fill=tk.X, pady=5)
        
        for i, (type_key, dimensions) in enumerate(ImageProcessor.DIMENSIONS.items()):
            type_name = type_key.capitalize()
            dim_text = f"{dimensions[0]}x{dimensions[1]} px"
            ttk.Radiobutton(
                type_frame, 
                text=f"{type_name} ({dim_text})", 
                value=type_key, 
                variable=self.image_type,
                command=self._update_preview
            ).pack(anchor=tk.W, pady=2)
        
        # Opciones adicionales
        options_frame = ttk.LabelFrame(control_frame, text="Opciones", padding=5)
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(
            options_frame, 
            text="Mantener relación de aspecto", 
            variable=self.maintain_aspect,
            command=self._update_preview
        ).pack(anchor=tk.W, pady=2)
        
        # Directorio de salida
        output_frame = ttk.Frame(control_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Directorio de salida:").pack(anchor=tk.W)
        
        output_path_frame = ttk.Frame(output_frame)
        output_path_frame.pack(fill=tk.X, pady=2)
        
        self.output_path_label = ttk.Label(
            output_path_frame, 
            text=self.output_dir,
            wraplength=200
        )
        self.output_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            output_path_frame, 
            text="...", 
            width=3,
            command=self._select_output_dir
        ).pack(side=tk.RIGHT)
        
        # Botones de acción
        action_frame = ttk.Frame(control_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            action_frame, 
            text="Convertir", 
            command=self._process_images,
            style="Accent.TButton"
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            action_frame, 
            text="Limpiar Selección", 
            command=self._clear_selection
        ).pack(fill=tk.X, pady=2)
        
        # Columna derecha: Vista previa y resultados
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Vista previa
        preview_label_frame = ttk.LabelFrame(preview_frame, text="Vista Previa", padding=10)
        preview_label_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        preview_container = ttk.Frame(preview_label_frame)
        preview_container.pack(fill=tk.BOTH, expand=True)
        
        # Dividir en dos para mostrar original y procesado
        self.preview_original_frame = ttk.LabelFrame(preview_container, text="Original")
        self.preview_original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Crear un frame para contener el label y el mensaje de arrastrar
        self.original_container = ttk.Frame(self.preview_original_frame)
        self.original_container.pack(fill=tk.BOTH, expand=True)
        
        # Label para mostrar el mensaje de arrastrar
        self.drag_label = ttk.Label(
            self.original_container, 
            text=self.drag_message,
            wraplength=250,
            justify=tk.CENTER,
            foreground="gray"
        )
        self.drag_label.pack(fill=tk.BOTH, expand=True)
        
        # Label para mostrar la imagen original
        self.preview_original_label = ttk.Label(self.original_container)
        
        # Configurar eventos de drag and drop para el frame original
        self.original_container.drop_target_register(tk.DND_FILES)
        self.original_container.dnd_bind('<<Drop>>', self._drop)
        self.drag_label.drop_target_register(tk.DND_FILES)
        self.drag_label.dnd_bind('<<Drop>>', self._drop)
        
        # Hacer que el frame original sea clickeable para seleccionar archivos
        self.original_container.bind("<Button-1>", lambda e: self._select_files())
        self.drag_label.bind("<Button-1>", lambda e: self._select_files())
        
        preview_processed_frame = ttk.LabelFrame(preview_container, text="Procesado")
        preview_processed_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.preview_processed_label = ttk.Label(preview_processed_frame)
        self.preview_processed_label.pack(fill=tk.BOTH, expand=True)
        
        # Navegación de vista previa
        preview_nav_frame = ttk.Frame(preview_label_frame)
        preview_nav_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            preview_nav_frame, 
            text="Anterior", 
            command=self._prev_preview
        ).pack(side=tk.LEFT)
        
        self.preview_index_label = ttk.Label(preview_nav_frame, text="")
        self.preview_index_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            preview_nav_frame, 
            text="Siguiente", 
            command=self._next_preview
        ).pack(side=tk.LEFT)
        
        # Historial de conversiones
        history_frame = ttk.LabelFrame(preview_frame, text="Historial de Conversiones", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crear un Treeview para el historial
        columns = ("fecha", "tipo", "archivos", "estado")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        
        # Definir encabezados
        self.history_tree.heading("fecha", text="Fecha")
        self.history_tree.heading("tipo", text="Tipo")
        self.history_tree.heading("archivos", text="Archivos")
        self.history_tree.heading("estado", text="Estado")
        
        # Configurar columnas
        self.history_tree.column("fecha", width=150)
        self.history_tree.column("tipo", width=100)
        self.history_tree.column("archivos", width=80)
        self.history_tree.column("estado", width=80)
        
        # Scrollbar para el Treeview
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar Treeview y scrollbar
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vincular evento de doble clic para abrir carpeta
        self.history_tree.bind("<Double-1>", self._open_history_folder)
        
        # Barra de estado
        self.status_var = tk.StringVar(value="Listo")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configurar estilo para botón de acento
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Default", 10, "bold"))
        
        # Inicializar TkinterDnD
        self._setup_drag_drop()
    
    def _setup_drag_drop(self):
        """Configura el sistema de arrastrar y soltar"""
        # Registrar el widget como objetivo de drop
        self.root.drop_target_register(tk.DND_FILES)
        self.root.dnd_bind('<<Drop>>', self._drop)
    
    def _drop(self, event):
        """Maneja el evento de soltar archivos"""
        # Obtener la ruta del archivo soltado
        files = event.data
        
        # En Windows, los archivos vienen como {ruta1} {ruta2}
        # En Linux/Mac, los archivos vienen como ruta1 ruta2
        if files.startswith('{') and files.endswith('}'):
            # Windows format: {file1} {file2}
            file_paths = []
            current = ""
            in_braces = False
            
            for char in files:
                if char == '{':
                    in_braces = True
                    current = ""
                elif char == '}':
                    in_braces = False
                    file_paths.append(current)
                elif in_braces:
                    current += char
        else:
            # Linux/Mac format: file1 file2
            file_paths = files.split()
        
        # Filtrar solo formatos soportados
        valid_files = [f for f in file_paths if ImageProcessor.is_supported_format(f)]
        
        if valid_files:
            self.input_files = valid_files
            self.files_label.config(text=f"{len(valid_files)} archivos seleccionados")
            
            # Actualizar vista previa
            self.current_preview_index = 0
            self._update_preview()
        else:
            messagebox.showwarning(
                "Formato no soportado", 
                "Los archivos seleccionados no son imágenes en formato soportado."
            )
    
    def _select_files(self):
        """Abre un diálogo para seleccionar archivos"""
        files = filedialog.askopenfilenames(
            title="Seleccionar Imágenes",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.gif"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if files:
            # Filtrar solo formatos soportados
            valid_files = [f for f in files if ImageProcessor.is_supported_format(f)]
            self.input_files = valid_files
            self.files_label.config(text=f"{len(valid_files)} archivos seleccionados")
            
            # Actualizar vista previa
            self.current_preview_index = 0
            self._update_preview()
    
    def _select_folder(self):
        """Abre un diálogo para seleccionar una carpeta"""
        folder = filedialog.askdirectory(title="Seleccionar Carpeta con Imágenes")
        
        if folder:
            # Obtener todos los archivos de la carpeta
            all_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if ImageProcessor.is_supported_format(file_path):
                        all_files.append(file_path)
            
            self.input_files = all_files
            self.files_label.config(text=f"{len(all_files)} archivos seleccionados")
            
            # Actualizar vista previa
            self.current_preview_index = 0
            self._update_preview()
    
    def _select_output_dir(self):
        """Abre un diálogo para seleccionar el directorio de salida"""
        folder = filedialog.askdirectory(title="Seleccionar Directorio de Salida")
        
        if folder:
            self.output_dir = folder
            self.output_path_label.config(text=folder)
    
    def _update_preview(self):
        """Actualiza la vista previa con la imagen actual"""
        if not self.input_files:
            # Mostrar mensaje de arrastrar
            if hasattr(self, 'preview_original_label'):
                self.preview_original_label.pack_forget()
            if hasattr(self, 'drag_label'):
                self.drag_label.pack(fill=tk.BOTH, expand=True)
            
            # Limpiar vista previa procesada
            self.preview_processed_label.config(image="")
            self.preview_index_label.config(text="")
            return
        
        # Ocultar mensaje de arrastrar y mostrar imagen
        if hasattr(self, 'drag_label'):
            self.drag_label.pack_forget()
        if hasattr(self, 'preview_original_label'):
            self.preview_original_label.pack(fill=tk.BOTH, expand=True)
        
        # Actualizar índice
        self.preview_index_label.config(
            text=f"Imagen {self.current_preview_index + 1} de {len(self.input_files)}"
        )
        
        # Obtener archivo actual
        current_file = self.input_files[self.current_preview_index]
        
        try:
            # Cargar imagen original
            img = Image.open(current_file)
            
            # Redimensionar para vista previa (manteniendo proporción)
            img_width, img_height = img.size
            max_size = 300
            
            if img_width > max_size or img_height > max_size:
                ratio = min(max_size / img_width, max_size / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                img_preview = img.resize((new_width, new_height), Image.LANCZOS)
            else:
                img_preview = img.copy()
            
            # Convertir a PhotoImage para Tkinter
            self.preview_original = ImageTk.PhotoImage(img_preview)
            self.preview_original_label.config(image=self.preview_original)
            
            # Crear vista previa procesada
            # Crear un archivo temporal para la vista previa
            temp_dir = os.path.join(os.path.expanduser("~"), ".opl_converter_temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            temp_file = os.path.join(temp_dir, "preview.png")
            
            # Procesar la imagen
            success, _ = ImageProcessor.convert_resize_image(
                current_file, 
                temp_file, 
                self.image_type.get(),
                self.maintain_aspect.get()
            )
            
            if success:
                # Cargar imagen procesada
                processed_img = Image.open(temp_file)
                
                # Redimensionar para vista previa si es necesario
                proc_width, proc_height = processed_img.size
                
                if proc_width > max_size or proc_height > max_size:
                    ratio = min(max_size / proc_width, max_size / proc_height)
                    new_width = int(proc_width * ratio)
                    new_height = int(proc_height * ratio)
                    proc_preview = processed_img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    proc_preview = processed_img.copy()
                
                # Convertir a PhotoImage para Tkinter
                self.preview_processed = ImageTk.PhotoImage(proc_preview)
                self.preview_processed_label.config(image=self.preview_processed)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la vista previa: {str(e)}")
    
    def _prev_preview(self):
        """Muestra la imagen anterior en la vista previa"""
        if self.input_files and self.current_preview_index > 0:
            self.current_preview_index -= 1
            self._update_preview()
    
    def _next_preview(self):
        """Muestra la siguiente imagen en la vista previa"""
        if self.input_files and self.current_preview_index < len(self.input_files) - 1:
            self.current_preview_index += 1
            self._update_preview()
    
    def _process_images(self):
        """Procesa las imágenes seleccionadas"""
        if not self.input_files:
            messagebox.showinfo("Información", "No hay archivos seleccionados para procesar.")
            return
        
        # Crear directorio de salida si no existe
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Obtener parámetros
        image_type = self.image_type.get()
        maintain_aspect = self.maintain_aspect.get()
        
        # Crear un directorio específico para esta conversión
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(self.output_dir, f"{image_type}_{timestamp}")
        os.makedirs(batch_dir)
        
        # Actualizar estado
        self.status_var.set(f"Procesando {len(self.input_files)} imágenes...")
        
        # Crear una función de progreso
        processed_count = [0]
        total_count = len(self.input_files)
        
        def update_progress(input_file, success, message):
            processed_count[0] += 1
            progress = processed_count[0] / total_count * 100
            self.status_var.set(f"Procesando... ({processed_count[0]}/{total_count}) - {progress:.1f}%")
            self.root.update_idletasks()
        
        # Ejecutar el procesamiento en un hilo separado
        def process_thread():
            results = ImageProcessor.batch_process(
                self.input_files,
                batch_dir,
                image_type,
                maintain_aspect,
                update_progress
            )
            
            # Contar resultados
            success_count = sum(1 for _, success, _ in results if success)
            
            # Actualizar historial
            history_entry = {
                "timestamp": timestamp,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "type": image_type,
                "total": len(self.input_files),
                "success": success_count,
                "directory": batch_dir
            }
            
            self.history.append(history_entry)
            self._save_history()
            self._update_history_tree()
            
            # Actualizar estado
            self.status_var.set(f"Completado: {success_count} de {len(self.input_files)} imágenes procesadas correctamente.")
            
            # Mostrar mensaje de finalización
            messagebox.showinfo(
                "Proceso Completado", 
                f"Se han procesado {success_count} de {len(self.input_files)} imágenes.\n"
                f"Las imágenes se guardaron en:\n{batch_dir}"
            )
        
        # Iniciar hilo
        threading.Thread(target=process_thread, daemon=True).start()
    
    def _clear_selection(self):
        """Limpia la selección de archivos"""
        self.input_files = []
        self.files_label.config(text="0 archivos seleccionados")
        
        # Mostrar mensaje de arrastrar
        if hasattr(self, 'preview_original_label'):
            self.preview_original_label.pack_forget()
        if hasattr(self, 'drag_label'):
            self.drag_label.pack(fill=tk.BOTH, expand=True)
        
        self.preview_processed_label.config(image="")
        self.preview_index_label.config(text="")
    
    def _load_history(self):
        """Carga el historial de conversiones"""
        history_file = os.path.join(os.path.expanduser("~"), ".opl_converter_history.txt")
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    lines = f.readlines()
                
                for line in lines:
                    parts = line.strip().split("|")
                    if len(parts) >= 6:
                        entry = {
                            "timestamp": parts[0],
                            "date": parts[1],
                            "type": parts[2],
                            "total": int(parts[3]),
                            "success": int(parts[4]),
                            "directory": parts[5]
                        }
                        self.history.append(entry)
                
                # Actualizar árbol de historial
                self._update_history_tree()
            except Exception as e:
                print(f"Error al cargar historial: {str(e)}")
    
    def _save_history(self):
        """Guarda el historial de conversiones"""
        history_file = os.path.join(os.path.expanduser("~"), ".opl_converter_history.txt")
        
        try:
            with open(history_file, "w") as f:
                for entry in self.history:
                    line = f"{entry['timestamp']}|{entry['date']}|{entry['type']}|{entry['total']}|{entry['success']}|{entry['directory']}\n"
                    f.write(line)
        except Exception as e:
            print(f"Error al guardar historial: {str(e)}")
    
    def _update_history_tree(self):
        """Actualiza el árbol de historial"""
        # Limpiar árbol
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Agregar entradas en orden inverso (más recientes primero)
        for entry in reversed(self.history):
            status = f"{entry['success']}/{entry['total']}"
            self.history_tree.insert(
                "", 
                "end", 
                values=(
                    entry['date'],
                    entry['type'].capitalize(),
                    entry['total'],
                    status
                ),
                tags=(entry['timestamp'],)
            )
    
    def _open_history_folder(self, event):
        """Abre la carpeta de una entrada del historial"""
        # Obtener ítem seleccionado
        selected_item = self.history_tree.selection()
        
        if not selected_item:
            return
        
        # Obtener timestamp del ítem
        timestamp = self.history_tree.item(selected_item[0], "tags")[0]
        
        # Buscar directorio correspondiente
        directory = None
        for entry in self.history:
            if entry['timestamp'] == timestamp:
                directory = entry['directory']
                break
        
        if directory and os.path.exists(directory):
            # Abrir carpeta en el explorador de archivos
            if os.name == 'nt':  # Windows
                os.startfile(directory)
            elif os.name == 'posix':  # macOS y Linux
                try:
                    # Intentar con xdg-open (Linux)
                    os.system(f'xdg-open "{directory}"')
                except:
                    # Intentar con open (macOS)
                    os.system(f'open "{directory}"')
        else:
            messagebox.showerror("Error", "No se pudo encontrar la carpeta o ya no existe.")


# Función principal para iniciar la aplicación
def main():
    # Importar TkinterDnD para arrastrar y soltar
    try:
        import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        # Si no está disponible TkinterDnD, usar Tk normal
        # y mostrar un mensaje de advertencia
        root = tk.Tk()
        messagebox.showwarning(
            "Funcionalidad limitada",
            "La biblioteca TkinterDnD no está instalada. La funcionalidad de arrastrar y soltar no estará disponible.\n\n"
            "Para instalarla, ejecute: pip install tkinterdnd2"
        )
        
        # Crear una clase ficticia para evitar errores
        class DummyDnD:
            def __init__(self, root):
                self.root = root
            
            def drop_target_register(self, *args):
                pass
            
            def dnd_bind(self, *args):
                pass
        
        # Agregar métodos ficticios a los widgets
        tk.Widget.drop_target_register = lambda self, *args: None
        tk.Widget.dnd_bind = lambda self, *args: None
    
    app = OPLImageConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()