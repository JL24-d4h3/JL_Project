-- Agregar tipo 'code' al constraint de tipos permitidos
-- Ejecutar como usuario postgres o dueño de la base de datos

\c cdn_dev

-- Eliminar constraint existente
ALTER TABLE content DROP CONSTRAINT IF EXISTS content_type_check;

-- Crear nuevo constraint con 'code' incluido
ALTER TABLE content ADD CONSTRAINT content_type_check
  CHECK (type IN ('video', 'pdf', 'audio', 'interactive', 'image', 'document', 'code'));

-- Verificar que se aplicó correctamente
\d content

SELECT 'Constraint actualizado exitosamente. Ahora se permiten archivos de código.' AS resultado;
