import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { ChevronDown, ChevronUp, Pause, Play, Repeat, Volume2, VolumeX } from 'lucide-react';
import VideoTemplate, { SCENE_DURATIONS } from './VideoTemplate';
import { useSceneControls } from './useSceneControls';

const SCENE_DETAILS: Record<string, { title: string; filePath: string }> = {
  opening: { title: 'Opening · Quote folio', filePath: 'src/components/video/FilmScenes.tsx' },
  costing: { title: 'Cost snapshot', filePath: 'src/components/video/FilmScenes.tsx' },
  references: { title: 'Price references', filePath: 'src/components/video/FilmScenes.tsx' },
  review: { title: 'Human review', filePath: 'src/components/video/FilmScenes.tsx' },
  archive: { title: 'Traceable record', filePath: 'src/components/video/FilmScenes.tsx' },
};

function announceSceneSelection(index: number, sceneKeys: string[]) {
  const key = sceneKeys[index];
  const details = SCENE_DETAILS[key];
  if (!details?.filePath) return;
  window.parent.postMessage({
    type: 'REPLIT_VIDEO_SCENE_SELECTED',
    payload: {
      sceneIndex: index,
      sceneCount: sceneKeys.length,
      sceneTitle: details.title || key,
      filePath: details.filePath,
      lineNumber: 1,
    },
  }, '*');
}

export default function VideoWithControls() {
  const isIframed = typeof window !== 'undefined' && window.self !== window.top;
  const [muted, setMuted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [tapPinned, setTapPinned] = useState(false);
  const sensorRef = useRef<HTMLDivElement | null>(null);
  const {
    sceneKeys, activeIndex, locked, paused, mountKey, tick,
    durations, activeDuration, activeStartTime, totalDuration,
    onSceneChange, jumpTo, toggleLock, togglePause,
  } = useSceneControls(SCENE_DURATIONS);

  const handleJumpTo = useCallback((index: number) => {
    jumpTo(index);
    announceSceneSelection(index, sceneKeys);
  }, [jumpTo, sceneKeys]);
  const handlePointerEnter = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse') setHovering(true);
  }, []);
  const handlePointerLeave = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse') setHovering(false);
  }, []);
  const handlePointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse' && collapsed) setTapPinned(true);
  }, [collapsed]);
  const handleToggleCollapsed = useCallback(() => {
    setCollapsed((current) => {
      if (!current) { setHovering(false); setTapPinned(false); }
      return !current;
    });
  }, []);

  useEffect(() => {
    if (!(collapsed && tapPinned)) return;
    const onDocumentPointerDown = (event: PointerEvent) => {
      if (event.pointerType === 'mouse') return;
      const sensor = sensorRef.current;
      if (sensor && !sensor.contains(event.target as Node)) setTapPinned(false);
    };
    document.addEventListener('pointerdown', onDocumentPointerDown);
    return () => document.removeEventListener('pointerdown', onDocumentPointerDown);
  }, [collapsed, tapPinned]);

  useEffect(() => {
    if (!paused) return;
    const frozen = document.getAnimations().filter((animation) => animation.playState === 'running');
    frozen.forEach((animation) => animation.pause());
    return () => frozen.forEach((animation) => animation.play());
  }, [paused]);

  if (!isIframed) return <VideoTemplate />;
  const barVisible = !collapsed || hovering || tapPinned;
  return (
    <div className="relative h-screen w-full">
      <VideoTemplate
        key={mountKey}
        durations={durations}
        loop
        paused={paused}
        muted={muted}
        onSceneChange={onSceneChange}
      />
      <div
        ref={sensorRef}
        className="control-sensor"
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
        onPointerDown={handlePointerDown}
      >
        <div className="control-sensor-filler" aria-hidden="true" />
        <div className={`control-bar ${barVisible ? 'is-visible' : ''}`} aria-hidden={!barVisible}>
          <button className="control-icon" onClick={togglePause} aria-label={paused ? 'Play' : 'Pause'} title={paused ? 'Play' : 'Pause'}>
            {paused ? <Play /> : <Pause />}
          </button>
          <button className={`control-icon ${locked ? 'is-active' : ''}`} onClick={toggleLock} aria-label={locked ? 'Loop current scene: on' : 'Loop current scene: off'} title={locked ? 'Loop current scene: on' : 'Loop current scene: off'} aria-pressed={locked}>
            <Repeat />
          </button>
          <button className="control-icon" onClick={() => setMuted((value) => !value)} aria-label={muted ? 'Unmute audio' : 'Mute audio'} title={muted ? 'Unmute audio' : 'Mute audio'} aria-pressed={muted}>
            {muted ? <VolumeX /> : <Volume2 />}
          </button>
          <div className="control-divider" aria-hidden="true" />
          <PlaybackStatus
            sceneKeys={sceneKeys}
            activeIndex={activeIndex}
            activeDuration={activeDuration}
            activeStartTime={activeStartTime}
            totalDuration={totalDuration}
            tick={tick}
            paused={paused}
            onJumpTo={handleJumpTo}
          />
          <button className="control-icon control-chevron" onClick={handleToggleCollapsed} title={collapsed ? 'Show controls' : 'Hide controls'} aria-label={collapsed ? 'Show controls' : 'Hide controls'} aria-expanded={!collapsed}>
            {collapsed ? <ChevronUp /> : <ChevronDown />}
          </button>
        </div>
      </div>
    </div>
  );
}

function PlaybackStatus({
  sceneKeys, activeIndex, activeDuration, activeStartTime, totalDuration,
  tick, paused, onJumpTo,
}: {
  sceneKeys: string[];
  activeIndex: number;
  activeDuration: number;
  activeStartTime: number;
  totalDuration: number;
  tick: number;
  paused: boolean;
  onJumpTo: (index: number) => void;
}) {
  const [elapsed, setElapsed] = useState(0);
  const elapsedBaseRef = useRef(0);

  useEffect(() => {
    setElapsed(0);
    elapsedBaseRef.current = 0;
  }, [tick]);
  useEffect(() => {
    if (paused) return;
    const startedAt = performance.now();
    const id = window.setInterval(() => setElapsed(elapsedBaseRef.current + performance.now() - startedAt), 60);
    return () => {
      window.clearInterval(id);
      elapsedBaseRef.current += performance.now() - startedAt;
    };
  }, [tick, paused]);

  const progress = activeDuration > 0 ? Math.min(1, elapsed / activeDuration) : 0;
  const totalElapsed = Math.min(totalDuration, activeStartTime + Math.min(elapsed, activeDuration));
  return (
    <>
      <div className="control-progress">
        {sceneKeys.map((key, index) => (
          <button
            key={key}
            className={`progress-segment ${index === activeIndex ? 'is-current' : ''}`}
            onClick={() => onJumpTo(index)}
            aria-label={`Jump to scene ${index + 1}`}
            aria-current={index === activeIndex ? 'true' : undefined}
          >
            <i style={{ transform: `scaleX(${index === activeIndex ? progress : 0})` }} />
          </button>
        ))}
      </div>
      <span className="control-counter">{activeIndex + 1}/{sceneKeys.length}</span>
      <span className="control-time" role="timer" aria-label={`Playback time ${formatTime(totalElapsed)} of ${formatTime(totalDuration)}`}>
        {formatTime(totalElapsed)} / {formatTime(totalDuration)}
      </span>
    </>
  );
}

function formatTime(durationMs: number): string {
  const seconds = Math.max(0, Math.floor(durationMs / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
