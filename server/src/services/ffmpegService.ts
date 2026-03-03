import ffmpeg from 'fluent-ffmpeg';
import path from 'path';
import fs from 'fs/promises';

const STORAGE_BASE = process.env.STORAGE_PATH || '/home/jleon/2026/PUCP/GTR/CDN/storage';
const FFMPEG_PATH = process.env.FFMPEG_PATH || '/usr/bin/ffmpeg';
const FFPROBE_PATH = process.env.FFPROBE_PATH || '/usr/bin/ffprobe';

// Configurar rutas de FFmpeg
ffmpeg.setFfmpegPath(FFMPEG_PATH);
ffmpeg.setFfprobePath(FFPROBE_PATH);

export interface VideoMetadata {
  duration: number; // segundos
  resolution: string; // "1920x1080"
  width: number;
  height: number;
  bitrate: number; // bps
  codec: string;
  fps: number;
  hasAudio: boolean;
}

export interface ThumbnailOptions {
  timestamp?: string; // "00:00:02"
  width?: number;
  height?: number;
}

/**
 * FFmpeg Service - Procesamiento de video/audio
 * Arquitectura: Service Layer Pattern
 */
export class FFmpegService {
  /**
   * Extrae metadata completa de un video usando ffprobe
   */
  async extractVideoMetadata(filePath: string): Promise<VideoMetadata> {
    return new Promise((resolve, reject) => {
      const fullPath = path.join(STORAGE_BASE, filePath);

      ffmpeg.ffprobe(fullPath, (err, metadata) => {
        if (err) {
          return reject(new Error(`FFprobe error: ${err.message}`));
        }

        const videoStream = metadata.streams.find((s) => s.codec_type === 'video');
        const audioStream = metadata.streams.find((s) => s.codec_type === 'audio');

        if (!videoStream) {
          return reject(new Error('No video stream found'));
        }

        const duration = metadata.format.duration || 0;
        const width = videoStream.width || 0;
        const height = videoStream.height || 0;
        const resolution = `${width}x${height}`;
        const bitrate = parseInt(String(metadata.format.bit_rate || '0'), 10);
        const codec = videoStream.codec_name || 'unknown';
        
        // FPS calculation
        let fps = 0;
        if (videoStream.r_frame_rate) {
          const [num, den] = videoStream.r_frame_rate.split('/').map(Number);
          fps = Math.round(num / den);
        }

        resolve({
          duration: Math.floor(duration),
          resolution,
          width,
          height,
          bitrate,
          codec,
          fps,
          hasAudio: !!audioStream,
        });
      });
    });
  }

  /**
   * Genera thumbnail de un video
   * Tiempo de captura: 2 segundos por defecto
   */
  async generateThumbnail(
    videoPath: string,
    outputName: string,
    options: ThumbnailOptions = {}
  ): Promise<string> {
    const {
      timestamp = '00:00:02',
      width = 640,
      height = -1, // Mantiene aspect ratio
    } = options;

    const fullVideoPath = path.join(STORAGE_BASE, videoPath);
    const thumbnailDir = path.join(STORAGE_BASE, 'thumbnails');
    
    // Crear directorio si no existe
    await fs.mkdir(thumbnailDir, { recursive: true });

    const outputPath = path.join(thumbnailDir, outputName);

    return new Promise((resolve, reject) => {
      ffmpeg(fullVideoPath)
        .screenshots({
          timestamps: [timestamp],
          filename: outputName,
          folder: thumbnailDir,
          size: `${width}x${height}`,
        })
        .on('end', () => {
          // Ruta relativa para DB
          const relativePath = path.join('thumbnails', outputName);
          resolve(relativePath);
        })
        .on('error', (err) => {
          reject(new Error(`Thumbnail generation error: ${err.message}`));
        });
    });
  }

  /**
   * Transcodifica video a múltiples calidades (preparado para escalabilidad)
   * Por ahora genera solo 720p, pero fácil extender a 1080p, 480p, 360p
   */
  async transcodeVideo(
    inputPath: string,
    quality: '720p' | '480p' | '360p'
  ): Promise<string> {
    const qualitySettings = {
      '720p': { width: 1280, height: 720, bitrate: '2500k' },
      '480p': { width: 854, height: 480, bitrate: '1000k' },
      '360p': { width: 640, height: 360, bitrate: '500k' },
    };

    const settings = qualitySettings[quality];
    const fullInputPath = path.join(STORAGE_BASE, inputPath);
    
    // Nombre de salida: original_720p.mp4
    const parsedPath = path.parse(inputPath);
    const outputName = `${parsedPath.name}_${quality}${parsedPath.ext}`;
    const outputPath = path.join(STORAGE_BASE, parsedPath.dir, outputName);

    return new Promise((resolve, reject) => {
      ffmpeg(fullInputPath)
        .videoCodec('libx264')
        .audioCodec('aac')

        .size(`${settings.width}x${settings.height}`)
        .videoBitrate(settings.bitrate)
        .outputOptions([
          '-preset fast', // Balance entre velocidad y compresión
          '-crf 23', // Calidad constante (18-28, 23 es bueno)
          '-movflags +faststart', // Optimización para streaming
        ])
        .output(outputPath)
        .on('progress', (progress) => {
          // Log progreso (útil para jobs en background)
          if (progress.percent) {
            console.log(`Transcoding ${quality}: ${Math.round(progress.percent)}%`);
          }
        })
        .on('end', () => {
          const relativePath = path.join(parsedPath.dir, outputName);
          resolve(relativePath);
        })
        .on('error', (err) => {
          reject(new Error(`Transcoding error: ${err.message}`));
        })
        .run();
    });
  }

  /**
   * Valida que el archivo es un video válido
   */
  async validateVideoFile(filePath: string): Promise<boolean> {
    try {
      await this.extractVideoMetadata(filePath);
      return true;
    } catch {
      return false;
    }
  }
}

export const ffmpegService = new FFmpegService();
