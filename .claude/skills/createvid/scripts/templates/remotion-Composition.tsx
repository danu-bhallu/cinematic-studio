import { Composition, AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { loadFont as loadBodoni } from "@remotion/google-fonts/BodoniModa";
import { loadFont as loadInter } from "@remotion/google-fonts/InterTight";
import { CameraMotionBlur } from "@remotion/motion-blur";
import { z } from "zod";

const { fontFamily: serif } = loadBodoni("normal", { weights: ["400", "700"], subsets: ["latin"] });
const { fontFamily: sans } = loadInter("normal", { weights: ["400", "600"], subsets: ["latin"] });

export const titleSchema = z.object({
  artist: z.string(),
  title: z.string(),
  date: z.string(),
  accent: z.string(),
});
type Props = z.infer<typeof titleSchema>;

// expo-out: fast arrival, long settle (reads "expensive")
const out = Easing.bezier(0.16, 1, 0.3, 1);
const inn = Easing.bezier(0.7, 0, 0.84, 0);

export const TitleCard: React.FC<Props> = ({ artist, title, date, accent }) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames, width } = useVideoConfig();
  const s = (sec: number) => sec * fps;
  const exitStart = durationInFrames - s(0.6);

  // artist name: tracking collapses from wide to tight while fading up
  const artistOpacity = interpolate(f, [s(0.1), s(0.9)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tracking = interpolate(f, [0, s(2.2)], [0.9, 0.42], { easing: out, extrapolateRight: "clamp" });

  // title: mask-reveal rising from a baseline (clip-path), staggered per word
  const words = title.split(" ");
  // rule line draws on
  const rule = interpolate(f, [s(0.6), s(1.6)], [0, 1], { easing: out, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dateOp = interpolate(f, [s(1.4), s(2.0)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // exit: everything pushes up and out (continues the upward vector)
  const exitY = interpolate(f, [exitStart, durationInFrames], [0, -140], { easing: inn, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const exitOp = interpolate(f, [exitStart, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const big = width * 0.16;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", transform: `translateY(${exitY}px)`, opacity: exitOp }}>
      <div style={{ fontFamily: sans, fontWeight: 600, fontSize: width * 0.028, letterSpacing: `${tracking}em`, color: "#f3eee6", opacity: artistOpacity, textTransform: "uppercase", marginBottom: width * 0.03, paddingLeft: `${tracking}em` }}>
        {artist}
      </div>
      <div style={{ display: "flex", gap: big * 0.22, flexWrap: "wrap", justifyContent: "center", maxWidth: width * 0.9 }}>
        {words.map((w, i) => {
          const st = s(0.35 + i * 0.12);
          const p = interpolate(f, [st, st + s(1.1)], [0, 1], { easing: out, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ overflow: "hidden", lineHeight: 1.05, paddingBottom: big * 0.08 }}>
              <div style={{ fontFamily: serif, fontStyle: "italic", fontSize: big, color: "#f3eee6", textShadow: "0 0 60px rgba(0,0,0,0.55)", transform: `translateY(${(1 - p) * 110}%)`, filter: `blur(${(1 - p) * 8}px)` }}>
                {w}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ height: 2, width: width * 0.5 * rule, background: accent, marginTop: width * 0.04 }} />
      <div style={{ fontFamily: sans, fontWeight: 400, fontSize: width * 0.024, letterSpacing: "0.35em", color: "#f3eee6", opacity: dateOp * 0.85, marginTop: width * 0.03, textTransform: "uppercase", paddingLeft: "0.35em" }}>
        {date}
      </div>
    </AbsoluteFill>
  );
};

const TitleWithBlur: React.FC<Props> = (p) => (
  <CameraMotionBlur shutterAngle={180} samples={6}>
    <TitleCard {...p} />
  </CameraMotionBlur>
);

export const MyComposition = () => (
  <>
    <Composition
      id="Title"
      component={TitleWithBlur}
      schema={titleSchema}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ artist: "Artist Name", title: "New Single", date: "Out Friday", accent: "#c8102e" }}
    />
  </>
);
