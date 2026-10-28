/**
 * Fluid Gradient v4 — Terra-style orbiting blobs + fluid UV push, magnetism, S-curve.
 * Optional grass lobe: set opts.grassWeight (0–1) and opts.grassColor — v5 uses this
 * on top of the Brendan palette without changing d/e/center.
 */
(function () {
  'use strict';

  /** Leo / Brendan brand terracotta — #DA654D (same as landing + Tailwind terracotta). */
  const LEO_TERRA_RGB = [218 / 255, 101 / 255, 77 / 255];
  const LEO_TEAL_RGB = [17 / 255, 94 / 255, 89 / 255];

  function compile(gl, type, src) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      const err = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error(err || 'shader compile failed');
    }
    return sh;
  }

  function link(gl, vs, fs) {
    const p = gl.createProgram();
    gl.attachShader(p, vs);
    gl.attachShader(p, fs);
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      const err = gl.getProgramInfoLog(p);
      gl.deleteProgram(p);
      throw new Error(err || 'program link failed');
    }
    return p;
  }

  const VS_BLIT = `#version 300 es
precision highp float;
layout(location=0) in vec2 aUv;
out vec2 vUv;
void main(){
  vUv = vec2(1.0 - aUv.x, 1.0 - aUv.y);
  gl_Position = vec4(aUv * 2.0 - 1.0, 0.0, 1.0);
}`;

  const FS_GRADIENT_GEN = `#version 300 es
precision highp float;
in vec2 vUv;
uniform float uTime;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform vec3 uColorC;
uniform vec3 uColorD;
uniform vec3 uColorE;
uniform vec3 uColorCenter;
uniform vec3 uColorMid;
uniform float uMagnetism;
uniform float uShapeOrbit;
uniform float uShapeLobe;
uniform float uShapeWind;
uniform float uShapeSCurve;
uniform vec3 uColorGrass;
uniform float uGrassWeight;
uniform float uPathVariant;
uniform float uWindFreqY;
uniform float uWindFreqX;
out vec4 fragColor;

/** Perceptual linear mix — use only on tight seams (terra↔sky center) to cut purple fringe;
 *  on broad terra/lobes it pulls orange+blue toward muddy grey; use mix() there instead. */
vec3 linMix3(vec3 a, vec3 b, float w) {
    w = clamp(w, 0.0, 1.0);
    vec3 la = pow(max(a, vec3(0.0)), vec3(2.1));
    vec3 lb = pow(max(b, vec3(0.0)), vec3(2.1));
    return pow(mix(la, lb, w), vec3(1.0 / 2.1));
}

vec3 permute3(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
float snoise2(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                       -0.577350269189626, 0.024390243902439);
    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = permute3(permute3(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m; m = m*m;
    vec3 x2 = 2.0 * fract(p * C.www) - 1.0;
    vec3 h2 = abs(x2) - 0.5;
    vec3 ox = floor(x2 + 0.5);
    vec3 a0 = x2 - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h2*h2);
    vec3 g;
    g.x = a0.x * x0.x + h2.x * x0.y;
    g.yz = a0.yz * x12.xz + h2.yz * x12.yw;
    return 130.0 * dot(m, g);
}

void main() {
    float t0 = uTime * 0.055;
    float t = t0;
    float tWarp = t0 * 0.7 + 0.14 * sin(t0 * 0.38);
    float tx = (t * 0.48 + 0.16 * sin(t * 0.58)) * uShapeOrbit;

    // Constant warp amount — no surge pulse that causes temporary deformations
    float warpAmt = 0.32;

    vec2 warp = vec2(
        snoise2(vUv * 0.4 + vec2(tWarp * 0.058, tWarp * 0.044)),
        snoise2(vUv * 0.4 + vec2(tWarp * 0.048, tWarp * 0.062) + 37.0)
    ) * warpAmt;

    vec2 uv = vUv + warp;

    // Wind: slow phase, configurable spatial frequency
    float windPhase = uTime * 0.15;
    float breath = sin(uTime * 0.18) * 0.5 + 0.5;
    float gust = (0.024 + 0.018 * breath) * uShapeWind;
    uv += vec2(
        sin(windPhase + vUv.y * uWindFreqY) * gust,
        cos(windPhase * 0.86 + vUv.x * uWindFreqX) * (gust * 0.92)
    );
    // Micro-drift: very slow, very subtle
    uv += vec2(
        sin(uTime * 0.09 + vUv.x * 3.1 + vUv.y * 2.4) * 0.006 * uShapeWind,
        cos(uTime * 0.07 + vUv.y * 2.9) * 0.005 * uShapeWind
    );

    vec3 color = uColorD;
    vec3 terra = clamp(uColorA * 1.5, 0.0, 1.0);

    float breathe1 = sin(t * 0.22) * 0.5 + 0.5;
    float breathe2 = sin(t * 0.28 + 2.0) * 0.5 + 0.5;

    float pv = clamp(uPathVariant, 0.0, 1.0);

    float terraScale1 = 0.24 + breathe1 * 0.22;
    float terraScale2 = 0.21 + breathe2 * 0.19;

    vec2 pTerra1 = vec2(
        0.5 + 0.50 * uShapeLobe * sin(tx * (0.26 + pv * 0.12) + 0.4 + pv * 2.65),
        0.5 + 0.44 * uShapeLobe * cos(tx * (0.19 - pv * 0.06) + pv * 1.05)
    );
    float dT1 = length((uv - pTerra1) / vec2(1.0 + breathe1 * 0.38, 1.0));
    float terra1 = smoothstep(terraScale1, 0.065, dT1);
    terra1 = pow(clamp(terra1, 0.0, 1.0), 1.12);

    vec2 pTerra2 = vec2(
        0.5 + 0.48 * uShapeLobe * cos(tx * (0.23 + pv * 0.1) + 2.0 + pv * 1.15),
        0.5 + 0.42 * uShapeLobe * sin(tx * (0.17 + pv * 0.09) + 1.0 - pv * 0.95)
    );
    float dT2 = length((uv - pTerra2) / vec2(1.0, 1.0 + breathe2 * 0.34));
    float terra2 = smoothstep(terraScale2, 0.055, dT2);
    terra2 = pow(clamp(terra2, 0.0, 1.0), 1.12);

    float terraW = 1.0 - (1.0 - terra1) * (1.0 - min(terra2 * 0.92, 0.99));
    color = mix(color, terra, terraW);

    vec2 pushDir1 = normalize(uv - pTerra1 + vec2(0.001));
    vec2 pushDir2 = normalize(uv - pTerra2 + vec2(0.001));
    float totalPushW = max(terra1, terra2);
    vec2 totalPush = (pushDir1 * terra1 * breathe1 * 0.26 + pushDir2 * terra2 * breathe2 * 0.22) * (0.65 + 0.35 * totalPushW);

    vec2 pCream = vec2(
        0.5 + 0.46 * uShapeLobe * sin(tx * 0.21 + 3.5 + pv * 0.85),
        0.5 + 0.38 * uShapeLobe * cos(tx * 0.18 + 0.8 - pv * 0.55)
    );
    pCream += totalPush * 1.55;
    float creamScale = 0.19 + (1.0 - breathe1) * 0.14;
    float dCr = length(uv - pCream);
    float cream = pow(smoothstep(creamScale, 0.055, dCr), 1.08);
    color = mix(color, uColorE * 1.15, cream * 0.92);

    vec2 pWhite = vec2(
        0.5 + 0.48 * uShapeLobe * cos(tx * 0.22 + 1.2 + pv * 0.4),
        0.5 + 0.40 * uShapeLobe * sin(tx * 0.20 + 2.5 - pv * 0.7)
    );
    pWhite += totalPush * 1.35;
    float whiteScale = 0.18 + (1.0 - breathe2) * 0.14;
    float dW = length(uv - pWhite);
    float white = pow(smoothstep(whiteScale, 0.055, dW), 1.08);
    color = mix(color, uColorB * 1.12, white * 0.92);

    float sx = vUv.x;
    float sWarpY = warp.y;
    float sNoise = snoise2(vUv * 0.9 + tWarp * 0.032) * 0.026;
    float sxP = sx + pv * 0.11;
    float seam = mix(1.0 - sx, 0.64 - 0.46 * sx + 0.07 * sin(sx * 4.2), pv);
    float h2w = mix(1.0, -0.72, pv);
    float sCurveLine = seam
        + 0.34 * uShapeSCurve * sin(sxP * 3.14159265 + pv * 1.05)
        + 0.07 * uShapeSCurve * sin(sx * 6.2831853 + pv * 0.8) * h2w
        + 0.05 * uShapeSCurve * sin(windPhase * 0.5 + sx * 4.5 + pv * 1.4)
        + sNoise + sWarpY * 0.38;
    float sBandWidth = 0.095 + breathe1 * 0.035;
    float sDist = abs(vUv.y - sCurveLine);
    float sBand = smoothstep(sBandWidth, 0.022, sDist);
    color = linMix3(color, terra, sBand * 0.88);

    float centerDist = length(uv - vec2(0.5));
    float centerSpread = mix(0.42, 0.08, uMagnetism);
    float centerStrength = mix(0.0, 1.58, uMagnetism);
    float centerW = exp(-centerDist * centerDist / centerSpread) * centerStrength;
    color = linMix3(color, uColorCenter, centerW / (1.0 + centerW));

    // Grass last: S-band + center were washing green out (linMix3 toward terra/sky).
    vec3 grassRgb = clamp(uColorGrass * 1.2, 0.0, 1.0);
    vec2 pGrass = vec2(
        0.5 + 0.42 * uShapeLobe * sin(tx * 0.31 + 4.75 + pv * 0.25),
        0.5 + 0.38 * uShapeLobe * cos(tx * 0.235 + 0.35 + pv * 0.3)
    );
    pGrass += totalPush * 1.22;
    pGrass = clamp(pGrass, vec2(0.04), vec2(0.96));
    float grassScale = 0.2 + breathe1 * 0.13;
    vec2 grassEll = vec2(1.0 + breathe1 * 0.32, 1.0 + breathe2 * 0.28);
    float dGrass = length((uv - pGrass) / grassEll);
    float grassMask = pow(smoothstep(grassScale, 0.056, dGrass), 1.06);
    color = mix(color, grassRgb, clamp(grassMask * uGrassWeight * 0.97, 0.0, 1.0));

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}`;

  const VS_PREVIEW = `#version 300 es
precision highp float;
layout(location=0) in vec3 aPosition;
layout(location=1) in vec2 aUv;
out vec2 vUv;
void main() {
  vUv = vec2(1.0 - aUv.x, 1.0 - aUv.y);
  gl_Position = vec4(aPosition, 1.0);
}`;

  /** Fragment shader — verbatim from ElevenLabs capture #2 (GLSL ES 3.00). */
  const FS_PREVIEW_CLONE = `#version 300 es
precision highp float;
in vec2 vUv;
uniform float uTime;
uniform float uCircleSize;
uniform float uAlpha;
uniform vec4 uAudioAverage;
uniform vec4 uAudioAverageInput;
uniform vec4 uCumulativeAudio;
uniform float uExposure;
uniform float uContrast;
uniform float uSaturation;
uniform float uNoiseOpacity;
uniform int uNoiseBlendMode;
uniform float uAnimatedNoise;
uniform float uNoiseSpeed;
uniform float uNoiseAmplitude;
uniform float uNoiseScale;
uniform float uSphereScale;
uniform float uSpherePower;
uniform vec3 uFluidColor;
uniform int uFluidBlendMode;
uniform float uFluidColorOpacity;
uniform float uRingColorOpacity;
uniform float uFbmScale;
uniform float uFbmPower;
uniform float uFbmAmplitude;
uniform float uFbmSpeed;
uniform float uFluidDisplace;
uniform sampler2D uTexture;
uniform sampler2D uFluidSimTexture;
uniform float uFadeInDuration;
uniform float uCornerRadius;
uniform vec2 uResolution;
uniform float uDpr;
uniform vec2 uTextureResolution;
out vec4 outColor;
vec2 getCoverUv(vec2 uv, vec2 containerRes, vec2 textureRes) {
    float containerAspect = containerRes.x / containerRes.y;
    float textureAspect = textureRes.x / textureRes.y;
    vec2 scale = vec2(1.0);
    if (containerAspect > textureAspect) {
        scale.y = textureAspect / containerAspect;
    } else {
        scale.x = containerAspect / textureAspect;
    }
    vec2 coverUv = (uv - 0.5) * scale + 0.5;
    return coverUv;
}
float sdRoundedBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}
vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
        i.z + vec4(0.0, i1.z, i2.z, 1.0))
        + i.y + vec4(0.0, i1.y, i2.y, 1.0))
        + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 1.0/7.0;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
vec3 contrast(vec3 color, float value) {
    return clamp(0.5 + (1.0 + value) * (color - 0.5), vec3(0.0), vec3(1.0));
}
vec3 exposure(vec3 color, float value) {
    return (1.0 + value) * color;
}
vec3 czm_saturation(vec3 rgb, float adjustment) {
    const vec3 W = vec3(0.2125, 0.7154, 0.0721);
    vec3 intensity = vec3(dot(rgb, W));
    return mix(intensity, rgb, adjustment);
}
vec3 blendMultiply_19_17(vec3 base, vec3 blend) {
	return base*blend;
}
vec3 blendMultiply_19_17(vec3 base, vec3 blend, float opacity) {
	return (blendMultiply_19_17(base, blend) * opacity + base * (1.0 - opacity));
}
float blendOverlay_9_12(float base, float blend) {
	return base<0.5?(2.0*base*blend):(1.0-2.0*(1.0-base)*(1.0-blend));
}
vec3 blendOverlay_9_12(vec3 base, vec3 blend) {
	return vec3(blendOverlay_9_12(base.r,blend.r),blendOverlay_9_12(base.g,blend.g),blendOverlay_9_12(base.b,blend.b));
}
vec3 blendHardLight_7_13(vec3 base, vec3 blend) {
	return blendOverlay_9_12(blend,base);
}
vec3 blendHardLight_7_13(vec3 base, vec3 blend, float opacity) {
	return (blendHardLight_7_13(base, blend) * opacity + base * (1.0 - opacity));
}
float random(in vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}
vec2 hash(vec2 p) {
    p = vec2(dot(p, vec2(2127.1, 81.17)), dot(p, vec2(1269.5, 283.37)));
    return fract(sin(p) * 43758.5453);
}
float filmGrainNoise(in vec2 uv) {
    return length(hash(vec2(uv.x, uv.y)));
}
float noise(in vec2 _st) {
    vec2 i = floor(_st);
    vec2 f = fract(_st);
    float a = random(i);
    float b = random(i + vec2(1.0, 0.0));
    float c = random(i + vec2(0.0, 1.0));
    float d = random(i + vec2(1.0, 1.0));
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(a, b, u.x) +
            (c - a) * u.y * (1.0 - u.x) +
            (d - b) * u.x * u.y;
}
#define NUM_OCTAVES 4
float fbm(in vec2 _st) {
    float v = 0.0;
    float a = 0.5;
    vec2 shift = vec2(100.0);
    mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.5));
    for (int i = 0; i < NUM_OCTAVES; ++i) {
        v += a * noise(_st);
        _st = rot * _st * 2.0 + shift;
        a *= 0.5;
    }
    return v;
}
void main() {
    vec3 color = vec3(vUv, 0.);
    float circleSize = uCircleSize - pow(uAudioAverageInput.x * .75, 3.) * .2;
    vec2 uv = vec2(1. - vUv.x, vUv.y);
    vec3 fluid = texture(uFluidSimTexture, vUv).rgb;
    vec2 rectSize = vec2(1., 1.) * circleSize;
    float cornerRadius = (uCornerRadius * uDpr / min(uResolution.x, uResolution.y)) * 2.0;
    float sphereScale = uSphereScale;
    float spherePower = uSpherePower;
    vec2 uvDot = ((uv - 0.5) * 2.);
    float sdfDist = sdRoundedBox(uvDot * 0.5, rectSize * 0.5, cornerRadius * 0.5);
    float maxDist = max(min(rectSize.x, rectSize.y) * 0.5 - cornerRadius * 0.5, 0.001);
    float d = 1.0 - clamp(-sdfDist / maxDist, 0.0, 1.0);
    d = sqrt(max(1.0 - d * d, 0.0));
    d = pow(d, spherePower);
    vec2 innerSize = rectSize * 0.5 - vec2(cornerRadius * 0.5);
    vec2 absUv = abs(uvDot * 0.5);
    vec2 edgeDist = max(absUv - innerSize, vec2(0.0));
    float cornerDist = length(edgeDist);
    vec2 axisNormal = sign(uvDot) * smoothstep(vec2(0.0), innerSize, absUv);
    vec2 cornerNormal = edgeDist / max(cornerDist, 0.001) * sign(uvDot);
    float cornerBlend = smoothstep(0.0, cornerRadius * 0.5, cornerDist);
    vec2 normalXY = mix(axisNormal, cornerNormal, cornerBlend) * (1.0 - d);
    vec3 normals = vec3(normalXY, d);
    vec2 uv_scale = 1./vec2(sphereScale);
    uvDot /= (vec2(d, d) + vec2(1.,1.)) * uv_scale;
    uvDot = (uvDot +1.) * 0.5;
    uv = uvDot;
    float fbmScale = uFbmScale;
    float fbmPower = uFbmPower;
    float fbmAmplitude = uFbmAmplitude;
    float fbmTime1 = uTime * uFbmSpeed;
    float fbmTime2 = uTime * (uFbmSpeed * .5) + uCumulativeAudio.x * .25;
    vec2 fbmUv = uv * fbmScale;
    vec2 q = vec2(0.);
    q.x = fbm( fbmUv + 0.00 * fbmTime1);
    q.y = fbm( fbmUv + vec2(1.0));
    vec2 r = vec2(0.);
    r.x = fbm( fbmUv + 1.0 * q + vec2(91.3, .55) + 0.15 * fbmTime2 );
    r.y = fbm( fbmUv + 1.0 * q - vec2(45.33, 1.2) + 0.126 * fbmTime2);
    float f = fbm(fbmUv+r);
    float ffbm = mix(0.8, 0.66, clamp((f*f)*fbmPower,0.0,1.0));
    ffbm = mix(ffbm, 0., clamp(length(q),0.0,1.0));
    ffbm = mix(ffbm, 1., clamp(length(r.x),0.0,1.0));
    float noiseTime1 = uTime * uNoiseSpeed * .5 + uCumulativeAudio.z * .1;
    float noiseX = snoise(vec3(vUv * uNoiseScale, noiseTime1));
    float noiseTime2 = uTime * uNoiseSpeed;
    float noiseY = snoise(vec3(vUv * uNoiseScale + vec2(54., 54.), noiseTime2));
    vec2 noiseDisp = vec2(noiseX, noiseY);
    noiseDisp *= 1. + uAudioAverage.z * .25;
    vec2 shapeUv = (vUv - 0.5) * 2.0;
    float shapeDist = sdRoundedBox(shapeUv * 0.5, rectSize * 0.5, cornerRadius * 0.5);
    float s = 1.;
    float shapeMask = smoothstep(0.0, -maxDist, shapeDist);
    shapeMask = shapeMask * shapeMask;
    float roll = uTime * 0.04;
    uv += vec2(sin(roll + vUv.y * 6.28318), cos(roll * 0.78 + vUv.x * 6.28318)) * 0.008;
    vec2 fv = fluid.rg;
    uv += -fv * uFluidDisplace;
    vec2 fbmDir = vec2(ffbm - 0.5);
    uv += fbmDir * fbmAmplitude * 0.92;
    uv += noiseDisp * uNoiseAmplitude * 0.72;
    vec2 coverUv = getCoverUv(uv, uResolution, uTextureResolution);
    vec3 gradient = texture(uTexture, coverUv).rgb;
    float innerRadius = 0.25;
    float noiseScale = 0.65 + uAudioAverage.x * .4;
    vec2 ringUv = (vUv - .5) * 2. * (1./uCircleSize);
    ringUv *= .75;
    float ang = atan(ringUv.y, ringUv.x);
    float len = length(ringUv);
    float v2, v3, cl;
    float r0, n0;
    float ringTime = (-uTime * .5) - uCumulativeAudio.a * .2;
    ringUv.x += 1. + uAudioAverage.y * 1.5 - uAudioAverageInput.y * 2.5;
    n0 = snoise( vec3(ringUv * noiseScale, ringTime * 0.5) ) * 0.5 + 0.5;
    r0 = mix(mix(innerRadius, 1.0, 0.75), mix(innerRadius, 1.0, 0.2), n0);
    cl = cos(ang + ringTime * 2.0) * 0.5 + 0.5;
    float a = -ringTime * 1.0;
    v2 = smoothstep(1.0, mix(innerRadius, 1.0, n0 * 0.5), len);
    v3 = pow(smoothstep(innerRadius, mix(innerRadius, 1.0, n0 * 0.75), len), 2.);
    cl = cl * v2 * v3;
    cl = clamp(pow(cl * min(uAudioAverage.a * 4. + uAudioAverageInput.x * 4., 1.), 3.), 0., 1.);
    color = gradient + (vec3(cl) * uRingColorOpacity);
    color = blendHardLight_7_13(color, uFluidColor, length(fluid) * .01 * uFluidColorOpacity);
    vec2 grainUv = vUv + vec2(uTime * 0.517, uTime * 0.733) * uAnimatedNoise;
    color = blendMultiply_19_17(color, vec3(filmGrainNoise(grainUv)), uNoiseOpacity);
    color = czm_saturation(color, uSaturation);
    color = contrast(color, uContrast);
    color = exposure(color, uExposure);
    float fadeIn = uFadeInDuration > 0.0 ? min(uTime / uFadeInDuration, 1.) : 1.;
    outColor.a = s * uAlpha * fadeIn;
    color = clamp(color, 0.0, 1.0);
    outColor.rgb = color * outColor.a;
}
`;

  function makePass(gl, fragSrc, name) {
    const fs = compile(gl, gl.FRAGMENT_SHADER, fragSrc);
    const vs = compile(gl, gl.VERTEX_SHADER, VS_BLIT);
    const prog = link(gl, vs, fs);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    const u = {};
    const n = gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const inf = gl.getActiveUniform(prog, i);
      if (inf) u[inf.name] = gl.getUniformLocation(prog, inf.name);
    }
    return { prog, u, name };
  }

  function makePreviewProgram(gl) {
    const vs = compile(gl, gl.VERTEX_SHADER, VS_PREVIEW);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FS_PREVIEW_CLONE);
    const prog = link(gl, vs, fs);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    const u = {};
    const n = gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const inf = gl.getActiveUniform(prog, i);
      if (inf) u[inf.name] = gl.getUniformLocation(prog, inf.name);
    }
    return { prog, u, name: 'previewClone' };
  }

  class DoubleFBO {
    constructor(gl, w, h, internalFormat, format, type, filter) {
      this.gl = gl;
      this.w = w;
      this.h = h;
      this.read = this._fbo(w, h, internalFormat, format, type, filter);
      this.write = this._fbo(w, h, internalFormat, format, type, filter);
    }
    _fbo(w, h, internalFormat, format, type, filter) {
      const gl = this.gl;
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, w, h, 0, format, type, null);
      const fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      if (st !== gl.FRAMEBUFFER_COMPLETE) {
        gl.deleteTexture(tex);
        gl.deleteFramebuffer(fbo);
        return null;
      }
      return { texture: tex, fbo, w, h };
    }
    get texelSize() {
      return [1 / this.w, 1 / this.h];
    }
    swap() {
      const t = this.read;
      this.read = this.write;
      this.write = t;
    }
    destroy(gl) {
      [this.read, this.write].forEach((fb) => {
        if (!fb) return;
        gl.deleteTexture(fb.texture);
        gl.deleteFramebuffer(fb.fbo);
      });
    }
    resize(w, h, internalFormat, format, type, filter) {
      const gl = this.gl;
      [this.read, this.write].forEach((fb) => {
        if (!fb) return;
        gl.deleteTexture(fb.texture);
        gl.deleteFramebuffer(fb.fbo);
      });
      this.w = w;
      this.h = h;
      this.read = this._fbo(w, h, internalFormat, format, type, filter);
      this.write = this._fbo(w, h, internalFormat, format, type, filter);
    }
  }

  class FluidGradientV4 {
    constructor(canvas, opts) {
      this.canvas = canvas;
      this.opts = opts || {};
      this.colorA = this.opts.colorA || LEO_TERRA_RGB;
      this.colorB = this.opts.colorB || LEO_TEAL_RGB;
      this.fluidColor = this.opts.fluidColor || [0.12, 0.42, 0.38];
      this.shapeOrbit = this.opts.shapeOrbit != null ? this.opts.shapeOrbit : 1.0;
      this.shapeLobe = this.opts.shapeLobe != null ? this.opts.shapeLobe : 1.0;
      this.shapeWind = this.opts.shapeWind != null ? this.opts.shapeWind : 1.0;
      this.shapeSCurve = this.opts.shapeSCurve != null ? this.opts.shapeSCurve : 1.0;
      this.grassColor = this.opts.grassColor || [100 / 255, 198 / 255, 92 / 255];
      this.grassWeight = this.opts.grassWeight != null ? this.opts.grassWeight : 0.0;
      this.pathVariant = this.opts.pathVariant != null ? this.opts.pathVariant : 0.0;
      // Wind spatial frequency: high values (5–6) give organic ripple but alias at low fps.
      // Story thumbnails pass ~2.0 to avoid jitter. Heroes stay at default 5.8 / 5.2.
      this.windFreqY = this.opts.windFreqY != null ? this.opts.windFreqY : 5.8;
      this.windFreqX = this.opts.windFreqX != null ? this.opts.windFreqX : 5.2;
      /** Cap render FPS to reduce GPU load on marketing pages (default ~24). */
      const _fc = this.opts.fpsCap;
      this.fpsCap =
        typeof _fc === 'number' && _fc > 0 && _fc <= 120 ? _fc : 24;
      /** No fake “audio” modulation (marketing heroes): stable uniforms, less jitter. */
      this.useStaticAudio = this.opts.useStaticAudio === true;
      this._lastRafWallMs = 0;
      this.time = 0;
      this.timeVisual = 0;
      this._timeVisualFast = 0;
      this._magnetismSmooth = 0;
      this._auAvgFast = null;
      this.simW = 128;
      this.simH = 128;
      this.pressureIters = 20;
      /** Legacy nominal step (~60fps); simulation uses `_simDt` from measured frame interval. */
      this.dt = 0.024;
      this._lastTick = null;
      this._simDt = 0.024;
      this.curlStrength = this.useStaticAudio ? 3 : 22;
      this.dissipationVel = 0.987;
      this.dissipationDye = 0.972;
      this.splatInterval = 0.45;
      this.lastSplatTime = 0;
      this.texW = 512;
      this.texH = 512;
      this._initGL();
      if (!this.gl) return;
      try {
        this._buildPrograms();
      } catch (e) {
        console.error('[FluidGradient] shader build failed', e);
        this.gl = null;
        return;
      }
      this._quadSim();
      this._quadPreview();
      this._initGradientFBO();
      this.resize();
      window.addEventListener('resize', () => this.resize());
      this._raf = this._tick.bind(this);
      requestAnimationFrame(this._raf);
    }

    _initGL() {
      const gl = this.canvas.getContext('webgl2', {
        alpha: true,
        antialias: false,
        depth: false,
        stencil: false,
        premultipliedAlpha: false,
      });
      this.gl = gl;
      if (!gl) {
        console.error('[FluidGradient] WebGL2 unavailable');
        return;
      }
      this.halfFloat = gl.getExtension('EXT_color_buffer_float');
      this.halfFloatHalf = gl.getExtension('EXT_color_buffer_half_float');
      this.floatTex = gl.getExtension('OES_texture_float_linear');
      this.linearFilter = this.floatTex ? gl.LINEAR : gl.NEAREST;
      this.texType = gl.HALF_FLOAT;
      this.velInternal = gl.RG16F;
      this.velFormat = gl.RG;
      this.dyeInternal = gl.RGBA16F;
      this.dyeFormat = gl.RGBA;
      if (!this.halfFloat && !this.halfFloatHalf) {
        console.error('[FluidGradient] EXT_color_buffer_float / half_float required');
        this.gl = null;
      }
    }

    _buildPrograms() {
      const gl = this.gl;
      const advect = `#version 300 es
precision highp float;
precision highp sampler2D;
in vec2 vUv;
uniform sampler2D uVelocity;
uniform sampler2D uSource;
uniform vec2 texelSize;
uniform float dt;
uniform float dissipation;
out vec4 fragColor;
void main(){
  vec2 coord = vUv - dt * texture(uVelocity, vUv).xy * texelSize;
  fragColor = dissipation * texture(uSource, coord);
  fragColor.a = 1.0;
}`;
      const divergence = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform vec2 texelSize;
uniform sampler2D uVelocity;
out vec4 fragColor;
void main(){
  vec2 vL = vUv - vec2(texelSize.x, 0.0);
  vec2 vR = vUv + vec2(texelSize.x, 0.0);
  vec2 vT = vUv + vec2(0.0, texelSize.y);
  vec2 vB = vUv - vec2(0.0, texelSize.y);
  float L = texture(uVelocity, vL).x;
  float R = texture(uVelocity, vR).x;
  float T = texture(uVelocity, vT).y;
  float B = texture(uVelocity, vB).y;
  vec2 C = texture(uVelocity, vUv).xy;
  if (vL.x < 0.0) { L = -C.x; }
  if (vR.x > 1.0) { R = -C.x; }
  if (vT.y > 1.0) { T = -C.y; }
  if (vB.y < 0.0) { B = -C.y; }
  float div = 0.5 * (R - L + T - B);
  fragColor = vec4(div, 0.0, 0.0, 1.0);
}`;
      const curl = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform vec2 texelSize;
uniform sampler2D uVelocity;
out vec4 fragColor;
void main(){
  vec2 vL = vUv - vec2(texelSize.x, 0.0);
  vec2 vR = vUv + vec2(texelSize.x, 0.0);
  vec2 vT = vUv + vec2(0.0, texelSize.y);
  vec2 vB = vUv - vec2(0.0, texelSize.y);
  float L = texture(uVelocity, vL).y;
  float R = texture(uVelocity, vR).y;
  float T = texture(uVelocity, vT).x;
  float B = texture(uVelocity, vB).x;
  float vorticity = R - L - T + B;
  fragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
}`;
      const vorticity = `#version 300 es
precision highp float;
precision highp sampler2D;
in vec2 vUv;
uniform vec2 texelSize;
uniform sampler2D uVelocity;
uniform sampler2D uCurl;
uniform float curl;
uniform float dt;
out vec4 fragColor;
void main(){
  vec2 vL = vUv - vec2(texelSize.x, 0.0);
  vec2 vR = vUv + vec2(texelSize.x, 0.0);
  vec2 vT = vUv + vec2(0.0, texelSize.y);
  vec2 vB = vUv - vec2(0.0, texelSize.y);
  float L = texture(uCurl, vL).x;
  float R = texture(uCurl, vR).x;
  float T = texture(uCurl, vT).x;
  float B = texture(uCurl, vB).x;
  float C = texture(uCurl, vUv).x;
  vec2 force = 0.5 * vec2(abs(T) - abs(B), abs(R) - abs(L));
  force /= length(force) + 0.0001;
  force *= curl * C;
  force.y *= -1.0;
  vec2 vel = texture(uVelocity, vUv).xy;
  fragColor = vec4(vel + force * dt, 0.0, 1.0);
}`;
      const pressure = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform vec2 texelSize;
uniform sampler2D uPressure;
uniform sampler2D uDivergence;
out vec4 fragColor;
void main(){
  vec2 vL = vUv - vec2(texelSize.x, 0.0);
  vec2 vR = vUv + vec2(texelSize.x, 0.0);
  vec2 vT = vUv + vec2(0.0, texelSize.y);
  vec2 vB = vUv - vec2(0.0, texelSize.y);
  float L = texture(uPressure, vL).x;
  float R = texture(uPressure, vR).x;
  float T = texture(uPressure, vT).x;
  float B = texture(uPressure, vB).x;
  float divergence = texture(uDivergence, vUv).x;
  float pressure = (L + R + B + T - divergence) * 0.25;
  fragColor = vec4(pressure, 0.0, 0.0, 1.0);
}`;
      const gradientSubtract = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform vec2 texelSize;
uniform sampler2D uPressure;
uniform sampler2D uVelocity;
out vec4 fragColor;
void main(){
  vec2 vL = vUv - vec2(texelSize.x, 0.0);
  vec2 vR = vUv + vec2(texelSize.x, 0.0);
  vec2 vT = vUv + vec2(0.0, texelSize.y);
  vec2 vB = vUv - vec2(0.0, texelSize.y);
  float L = texture(uPressure, vL).x;
  float R = texture(uPressure, vR).x;
  float T = texture(uPressure, vT).x;
  float B = texture(uPressure, vB).x;
  vec2 velocity = texture(uVelocity, vUv).xy;
  velocity.xy -= vec2(R - L, T - B);
  fragColor = vec4(velocity, 0.0, 1.0);
}`;
      const blur = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform sampler2D uTexture;
uniform float value;
uniform vec2 simRes;
uniform vec2 direction;
out vec4 fragColor;
vec4 blur9(sampler2D image, vec2 uv, vec2 resolution, vec2 direction) {
  vec4 color = vec4(0.0);
  vec2 off1 = vec2(1.3846153846) * direction;
  vec2 off2 = vec2(3.2307692308) * direction;
  color += texture(image, uv) * 0.2270270270;
  color += texture(image, uv + (off1 / resolution)) * 0.3162162162;
  color += texture(image, uv - (off1 / resolution)) * 0.3162162162;
  color += texture(image, uv + (off2 / resolution)) * 0.0702702703;
  color += texture(image, uv - (off2 / resolution)) * 0.0702702703;
  return color;
}
void main(){
  fragColor = blur9(uTexture, vUv, simRes, direction);
}`;
      /** ElevenLabs splat dye #6 — center-based ring pulses (capture verbatim) */
      const splatDye = `#version 300 es
precision highp float;
precision highp sampler2D;
in vec2 vUv;
uniform sampler2D uTarget;
uniform vec3 color;
uniform float radius;
uniform float time;
uniform vec4 cumulativeAudio;
uniform vec4 audioAverage;
const float width = .15;
out vec4 fragColor;
void main () {
  vec2 p = vUv - vec2(.5);
  p *= radius;
  float dist = sqrt(dot(p, p));
  float pTime = time * .25 + cumulativeAudio.a * .15;
  float pDist = mod(dist * 2. - pTime, 1.);
  float pulse = smoothstep(0., width, pDist) - smoothstep(width, width * 2., pDist);
  vec3 splat = pulse * (audioAverage.x * 30.) * clamp(dist * 1., 0., 1.) * color;
  vec3 base = texture(uTarget, vUv).xyz;
  fragColor = vec4(base + splat, 1.0);
}`;
      const splatVel = `#version 300 es
precision highp float;
precision highp sampler2D;
in vec2 vUv;
uniform sampler2D uTarget;
uniform vec2 point;
uniform float radius;
uniform vec2 force;
uniform float aspectRatio;
out vec4 fragColor;
void main(){
  vec2 p = vUv - point;
  p.x *= aspectRatio;
  float d = length(p);
  float falloff = exp(-d * d / (radius * radius));
  vec2 v = texture(uTarget, vUv).xy;
  fragColor = vec4(v + force * falloff, 0.0, 1.0);
}`;
      const clear = `#version 300 es
precision mediump float;
precision mediump sampler2D;
in vec2 vUv;
uniform sampler2D uTexture;
uniform float value;
out vec4 fragColor;
void main(){
  fragColor = value * texture(uTexture, vUv);
}`;
      this.p = {
        advect: makePass(gl, advect, 'advect'),
        divergence: makePass(gl, divergence, 'divergence'),
        curl: makePass(gl, curl, 'curl'),
        vorticity: makePass(gl, vorticity, 'vorticity'),
        pressure: makePass(gl, pressure, 'pressure'),
        gradientSubtract: makePass(gl, gradientSubtract, 'gradientSubtract'),
        blur: makePass(gl, blur, 'blur'),
        splatDye: makePass(gl, splatDye, 'splatDye'),
        splatVel: makePass(gl, splatVel, 'splatVel'),
        clear: makePass(gl, clear, 'clear'),
        gradientGen: makePass(gl, FS_GRADIENT_GEN, 'gradientGen'),
        preview: makePreviewProgram(gl),
      };
    }

    _initGradientFBO() {
      const gl = this.gl;
      const gw = 512, gh = 512;
      this.texW = gw;
      this.texH = gh;
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gw, gh, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      const fbo = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      if (st !== gl.FRAMEBUFFER_COMPLETE) {
        console.error('[FluidGradient] gradient FBO init failed');
        gl.deleteTexture(tex);
        gl.deleteFramebuffer(fbo);
        return;
      }
      this.gradientFbo = { texture: tex, fbo, w: gw, h: gh };
      this.gradientColors = this.opts.gradientColors || {
        a: [...LEO_TERRA_RGB],
        b: [0.96, 0.96, 0.97],
        c: [0.20, 0.19, 0.18],
        d: [0.58, 0.78, 0.88],
        e: [0.94, 0.88, 0.80],
        mid: [...LEO_TERRA_RGB],
        center: [0.65, 0.82, 0.92],
      };
    }

    _renderGradient(t) {
      const gl = this.gl;
      this._setTarget(this.gradientFbo);
      this._bindSim();
      const pg = this.p.gradientGen;
      gl.useProgram(pg.prog);
      const c = this.gradientColors;
      const mid = c.mid || [0.82, 0.361, 0.269];
      gl.uniform1f(pg.u.uTime, t);
      gl.uniform3f(pg.u.uColorA, c.a[0], c.a[1], c.a[2]);
      gl.uniform3f(pg.u.uColorB, c.b[0], c.b[1], c.b[2]);
      gl.uniform3f(pg.u.uColorC, c.c[0], c.c[1], c.c[2]);
      gl.uniform3f(pg.u.uColorD, c.d[0], c.d[1], c.d[2]);
      gl.uniform3f(pg.u.uColorE, c.e[0], c.e[1], c.e[2]);
      gl.uniform3f(pg.u.uColorMid, mid[0], mid[1], mid[2]);
      gl.uniform3f(pg.u.uColorCenter, c.center[0], c.center[1], c.center[2]);
      gl.uniform1f(pg.u.uMagnetism, this._magnetism || 0.5);
      gl.uniform1f(pg.u.uShapeOrbit, this.shapeOrbit);
      gl.uniform1f(pg.u.uShapeLobe, this.shapeLobe);
      gl.uniform1f(pg.u.uShapeWind, this.shapeWind);
      gl.uniform1f(pg.u.uShapeSCurve, this.shapeSCurve);
      gl.uniform3f(pg.u.uColorGrass, this.grassColor[0], this.grassColor[1], this.grassColor[2]);
      gl.uniform1f(pg.u.uGrassWeight, this.grassWeight);
      gl.uniform1f(pg.u.uPathVariant, this.pathVariant);
      gl.uniform1f(pg.u.uWindFreqY, this.windFreqY);
      gl.uniform1f(pg.u.uWindFreqX, this.windFreqX);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }

    _quadSim() {
      const gl = this.gl;
      const verts = new Float32Array([0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1]);
      this.vboSim = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vboSim);
      gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);
      this.vaoSim = gl.createVertexArray();
      gl.bindVertexArray(this.vaoSim);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindVertexArray(null);
    }

    _quadPreview() {
      const gl = this.gl;
      const interleaved = new Float32Array([
        -1, -1, 0, 0, 0,
        1, -1, 0, 1, 0,
        -1, 1, 0, 0, 1,
        -1, 1, 0, 0, 1,
        1, -1, 0, 1, 0,
        1, 1, 0, 1, 1,
      ]);
      this.vboPreview = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vboPreview);
      gl.bufferData(gl.ARRAY_BUFFER, interleaved, gl.STATIC_DRAW);
      this.vaoPreview = gl.createVertexArray();
      gl.bindVertexArray(this.vaoPreview);
      const stride = 5 * 4;
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 3, gl.FLOAT, false, stride, 0);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 2, gl.FLOAT, false, stride, 12);
      gl.bindVertexArray(null);
    }

    _bindSim() {
      const gl = this.gl;
      gl.bindVertexArray(this.vaoSim);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vboSim);
    }

    _bindPreview() {
      const gl = this.gl;
      gl.bindVertexArray(this.vaoPreview);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vboPreview);
    }

    _setTarget(fbo) {
      const gl = this.gl;
      if (fbo) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.fbo);
        gl.viewport(0, 0, fbo.w, fbo.h);
      } else {
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, this.viewW, this.viewH);
      }
    }

    _blit(pass, setUniforms) {
      const gl = this.gl;
      gl.useProgram(pass.prog);
      if (setUniforms) setUniforms(pass.u);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }

    resize() {
      const parent = this.canvas.parentElement;
      if (!parent || !this.gl) return;
      const rect = parent.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const vw = Math.max(1, Math.floor(rect.width * dpr));
      const vh = Math.max(1, Math.floor(rect.height * dpr));
      this.viewW = vw;
      this.viewH = vh;
      this.dpr = dpr;
      this.canvas.width = vw;
      this.canvas.height = vh;
      this.canvas.style.width = rect.width + 'px';
      this.canvas.style.height = rect.height + 'px';
      const aspect = rect.width / Math.max(rect.height, 1);
      let sw = Math.round(144 * Math.max(1, aspect));
      let sh = Math.round(144 / Math.max(0.5, aspect));
      sw = Math.min(256, Math.max(96, sw));
      sh = Math.min(256, Math.max(96, sh));
      if (!this.velocity) {
        this._createBuffers(sw, sh);
      } else if (this.simW !== sw || this.simH !== sh) {
        this._recreateBuffers(sw, sh);
      }
    }

    _createBuffers(sw, sh) {
      const gl = this.gl;
      this.simW = sw;
      this.simH = sh;
      this.velocity = new DoubleFBO(gl, sw, sh, this.velInternal, this.velFormat, this.texType, this.linearFilter);
      this.dye = new DoubleFBO(gl, sw, sh, this.dyeInternal, this.dyeFormat, this.texType, this.linearFilter);
      this.divergence = this.velocity._fbo(sw, sh, gl.R16F, gl.RED, this.texType, this.linearFilter);
      this.curl = this.velocity._fbo(sw, sh, gl.R16F, gl.RED, this.texType, this.linearFilter);
      this.pressure = new DoubleFBO(gl, sw, sh, gl.R16F, gl.RED, this.texType, gl.NEAREST);
      if (!this.velocity.read || !this.dye.read || !this.divergence || !this.curl || !this.pressure.read) {
        console.error('[FluidGradient] FBO init failed');
      }
    }

    _recreateBuffers(sw, sh) {
      const gl = this.gl;
      this.velocity.destroy(gl);
      this.dye.destroy(gl);
      this.pressure.destroy(gl);
      if (this.divergence) {
        gl.deleteTexture(this.divergence.texture);
        gl.deleteFramebuffer(this.divergence.fbo);
      }
      if (this.curl) {
        gl.deleteTexture(this.curl.texture);
        gl.deleteFramebuffer(this.curl.fbo);
      }
      if (this.blurFbo) {
        gl.deleteTexture(this.blurFbo.texture);
        gl.deleteFramebuffer(this.blurFbo.fbo);
        this.blurFbo = null;
      }
      this._createBuffers(sw, sh);
    }

    /**
     * Fake “audio” for the Eleven-style preview: slow swell + tide envelopes and
     * low-frequency carriers (no fast beating). tanh soft-clips mixes for round peaks.
     */
    _syntheticAudio(t) {
      const breath = Math.sin(t * 0.076) * 0.5 + 0.5;
      const tide = Math.sin(t * 0.028 + 1.35) * 0.5 + 0.5;
      const swell = breath * breath;
      const env = swell * (0.2 + 0.8 * tide);

      const roll = Math.sin(t * 0.044 + 0.25) * 0.5 + 0.5;
      const tail = 0.5 + 0.5 * Math.sin(t * 0.019 + 0.7);
      const tailW = 0.42 + 0.58 * roll * tail;

      const soft = (x) => Math.tanh(x * 0.9);
      const m0 =
        soft(Math.sin(t * 0.112 + 0.15) * 0.55 + Math.sin(t * 0.071 + 0.95) * 0.38);
      const m1 =
        soft(Math.cos(t * 0.098 + 1.05) * 0.52 + Math.sin(t * 0.064 + 0.2) * 0.4);
      const m2 = soft(Math.sin(t * 0.086 + 2.15) * 0.62 + Math.cos(t * 0.052 + 0.4) * 0.28);
      const m3 = soft(Math.cos(t * 0.104 + 0.45) * 0.48 + Math.sin(t * 0.073 + 1.2) * 0.42);

      const avg = new Float32Array([
        0.028 + env * tailW * 0.032 * (0.5 + 0.5 * m0),
        0.024 + env * tailW * 0.028 * (0.5 + 0.5 * m1),
        0.006 + env * tailW * 0.022 * (0.5 + 0.5 * m2),
        0.026 + env * tailW * 0.026 * (0.5 + 0.5 * m3),
      ]);

      const i0 = soft(Math.sin(t * 0.102 + 0.55) * 0.5);
      const i1 = soft(Math.cos(t * 0.088 + 1.25) * 0.55);
      const i3 = soft(Math.sin(t * 0.067 + 0.1) * 0.35);

      const avgIn = new Float32Array([
        0.016 + env * tailW * 0.014 * (0.5 + 0.5 * i0),
        0.014 + env * tailW * 0.012 * (0.5 + 0.5 * i1),
        0.008 + env * tailW * 0.008 * (0.5 + 0.5 * m2),
        0.022 + env * tailW * 0.01 * (0.5 + 0.5 * i3),
      ]);

      return {
        avg,
        avgIn,
        cum: new Float32Array([t * 0.13, t * 0.082, t * 0.065, t * 0.098]),
      };
    }

    /**
     * Constant band levels + linear cum only — preview shader stays balanced without
     * frame-varying “audio” (removes micro-jitter on landing heroes).
     */
    _staticPreviewAudio(t) {
      return {
        avg: new Float32Array([0.032, 0.028, 0.022, 0.026]),
        avgIn: new Float32Array([0.018, 0.016, 0.014, 0.02]),
        cum: new Float32Array([
          t * 0.13,
          t * 0.082,
          t * 0.065,
          t * 0.098,
        ]),
      };
    }

    /**
     * Two-stage low-pass on avg / avgIn: fast stage follows target, slow stage trails
     * for a longer decay tail (less frame-to-frame jitter from uniforms).
     */
    _smoothPreviewAudio(au) {
      const fast = 0.2;
      const slow = 0.085;
      if (!this._auAvgFast) {
        this._auAvgFast = Float32Array.from(au.avg);
        this._auAvg = Float32Array.from(au.avg);
        this._auAvgInFast = Float32Array.from(au.avgIn);
        this._auAvgIn = Float32Array.from(au.avgIn);
        return { avg: this._auAvg, avgIn: this._auAvgIn, cum: au.cum };
      }
      for (let i = 0; i < 4; i++) {
        this._auAvgFast[i] += (au.avg[i] - this._auAvgFast[i]) * fast;
        this._auAvg[i] += (this._auAvgFast[i] - this._auAvg[i]) * slow;
        this._auAvgInFast[i] += (au.avgIn[i] - this._auAvgInFast[i]) * fast;
        this._auAvgIn[i] += (this._auAvgInFast[i] - this._auAvgIn[i]) * slow;
      }
      return { avg: this._auAvg, avgIn: this._auAvgIn, cum: au.cum };
    }

    /**
     * Two-pole exponential toward sim time — no spring overshoot / snap-back (plastic drift).
     * Convex combos only; cannot ring past the target like a damped oscillator.
     */
    _advanceVisualTime(dt) {
      const target = this.time;
      if (!Number.isFinite(dt) || dt <= 0) return;
      const tau1 = 0.1;
      const tau2 = 0.32;
      const k1 = 1 - Math.exp(-dt / tau1);
      const k2 = 1 - Math.exp(-dt / tau2);
      this._timeVisualFast += (target - this._timeVisualFast) * k1;
      this.timeVisual += (this._timeVisualFast - this.timeVisual) * k2;
      if (!Number.isFinite(this.timeVisual) || !Number.isFinite(this._timeVisualFast)) {
        this._timeVisualFast = target;
        this.timeVisual = target;
      }
    }

    _tick() {
      if (!this.gl || !this.velocity || !this.velocity.read) {
        requestAnimationFrame(this._raf);
        return;
      }
      const wallMs = performance.now();
      const minStepMs = 1000 / this.fpsCap;
      if (this._lastRafWallMs > 0 && wallMs - this._lastRafWallMs < minStepMs) {
        requestAnimationFrame(this._raf);
        return;
      }
      this._lastRafWallMs = wallMs;
      const now = wallMs * 0.001;
      let frameDt;
      if (this._lastTick == null) {
        this._lastTick = now;
        frameDt = 1 / 60;
      } else {
        frameDt = now - this._lastTick;
        this._lastTick = now;
        frameDt = Math.min(Math.max(frameDt, 1 / 240), 1 / 24);
      }
      // Match old fixed 0.024 @ 60fps: 0.024 * fps = 1.44 sim-units / real second.
      this._simDt = frameDt * 1.44;
      this.time += this._simDt;
      this._advanceVisualTime(frameDt);
      this._step();
      if (!this._readyFired) {
        this._readyFired = true;
        this.canvas.classList.add('leo-fluid-ready');
        const hero = this.canvas.closest('.hero-fluid-live');
        if (hero) {
          setTimeout(() => hero.classList.add('leo-hero-revealed'), 60);
        }
      }
      requestAnimationFrame(this._raf);
    }

    _step() {
      const gl = this.gl;
      gl.disable(gl.BLEND);
      const w = this.simW;
      const h = this.simH;
      const texel = [1 / w, 1 / h];
      const aspect = w / h;
      const t = this.time;
      const tVis = this.timeVisual;
      let au;
      if (this.useStaticAudio) {
        au = this._staticPreviewAudio(tVis);
      } else {
        const auRaw = this._syntheticAudio(tVis);
        const auCum = new Float32Array([
          tVis * 0.13,
          tVis * 0.082,
          tVis * 0.065,
          tVis * 0.098,
        ]);
        au = this._smoothPreviewAudio({ ...auRaw, cum: auCum });
      }

      const shouldSplat = t - this.lastSplatTime > this.splatInterval;
      if (shouldSplat) {
        this.lastSplatTime = t;
        const splatIdx = Math.floor(t / this.splatInterval) % 5;
        // Marketing heroes: minimal splat force — just enough to keep the sim alive
        // without causing visible deformations
        const forceScale = this.useStaticAudio ? 8 : 68;
        const splatConfigs = [
          { c: this.colorA, fv: [Math.cos(t * 0.56), Math.sin(t * 0.45)] },
          { c: this.colorB, fv: [-Math.sin(t * 0.4), Math.cos(t * 0.35)] },
          { c: this.colorA, fv: [0.7 * Math.sin(t * 0.29), -0.6 * Math.cos(t * 0.24)] },
          { c: this.colorB, fv: [-Math.cos(t * 0.32), -Math.sin(t * 0.26)] },
          { c: this.colorA, fv: [Math.sin(t * 0.23), Math.cos(t * 0.48)] },
        ];
        const s = splatConfigs[splatIdx];
        const dyeColor =
          this.grassWeight > 0.01 && splatIdx === 2 ? this.grassColor : s.c;
        const px = 0.5 + 0.35 * Math.sin(t * 0.35 + splatIdx * 1.26);
        const py = 0.5 + 0.3 * Math.cos(t * 0.29 + splatIdx * 0.9);

        this._setTarget(this.velocity.write);
        this._bindSim();
        this._blit(this.p.splatVel, (u) => {
          gl.uniform1i(u.uTarget, 0);
          gl.activeTexture(gl.TEXTURE0);
          gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
          gl.uniform2f(u.point, px, py);
          gl.uniform1f(u.radius, 0.14 + 0.03 * Math.sin(t * 0.64));
          gl.uniform2f(u.force, s.fv[0] * forceScale * this._simDt, s.fv[1] * forceScale * this._simDt);
          gl.uniform1f(u.aspectRatio, aspect);
        });
        this.velocity.swap();

        this._setTarget(this.dye.write);
        this._bindSim();
        this._blit(this.p.splatDye, (u) => {
          gl.uniform1i(u.uTarget, 0);
          gl.activeTexture(gl.TEXTURE0);
          gl.bindTexture(gl.TEXTURE_2D, this.dye.read.texture);
          gl.uniform3f(u.color, dyeColor[0], dyeColor[1], dyeColor[2]);
          gl.uniform1f(u.radius, 1.35);
          gl.uniform1f(u.time, t);
          gl.uniform4f(u.cumulativeAudio, au.cum[0], au.cum[1], au.cum[2], au.cum[3]);
          gl.uniform4f(u.audioAverage, au.avg[0], au.avg[1], au.avg[2], au.avg[3]);
        });
        this.dye.swap();
      }

      this._setTarget(this.velocity.write);
      this._bindSim();
      this._blit(this.p.advect, (u) => {
        gl.uniform2f(u.texelSize, texel[0], texel[1]);
        gl.uniform1f(u.dt, this._simDt);
        gl.uniform1f(u.dissipation, this.dissipationVel);
        gl.uniform1i(u.uVelocity, 0);
        gl.uniform1i(u.uSource, 1);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
      });
      this.velocity.swap();

      this._setTarget(this.curl);
      this._bindSim();
      gl.useProgram(this.p.curl.prog);
      gl.uniform2f(this.p.curl.u.texelSize, texel[0], texel[1]);
      gl.uniform1i(this.p.curl.u.uVelocity, 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
      gl.drawArrays(gl.TRIANGLES, 0, 6);

      this._setTarget(this.velocity.write);
      this._bindSim();
      this._blit(this.p.vorticity, (u) => {
        gl.uniform2f(u.texelSize, texel[0], texel[1]);
        gl.uniform1f(u.curl, this.curlStrength);
        gl.uniform1f(u.dt, this._simDt);
        gl.uniform1i(u.uVelocity, 0);
        gl.uniform1i(u.uCurl, 1);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.curl.texture);
      });
      this.velocity.swap();

      this._setTarget(this.divergence);
      this._bindSim();
      gl.useProgram(this.p.divergence.prog);
      gl.uniform2f(this.p.divergence.u.texelSize, texel[0], texel[1]);
      gl.uniform1i(this.p.divergence.u.uVelocity, 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
      gl.drawArrays(gl.TRIANGLES, 0, 6);

      let pRead = this.pressure.read;
      let pWrite = this.pressure.write;
      gl.bindFramebuffer(gl.FRAMEBUFFER, pRead.fbo);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.bindFramebuffer(gl.FRAMEBUFFER, pWrite.fbo);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);

      for (let it = 0; it < this.pressureIters; it++) {
        this._setTarget(pWrite);
        this._bindSim();
        gl.useProgram(this.p.pressure.prog);
        gl.uniform2f(this.p.pressure.u.texelSize, texel[0], texel[1]);
        gl.uniform1i(this.p.pressure.u.uPressure, 0);
        gl.uniform1i(this.p.pressure.u.uDivergence, 1);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, pRead.texture);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.divergence.texture);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        const tmp = pRead;
        pRead = pWrite;
        pWrite = tmp;
      }
      this.pressure.read = pRead;
      this.pressure.write = pWrite;

      this._setTarget(this.velocity.write);
      this._bindSim();
      this._blit(this.p.gradientSubtract, (u) => {
        gl.uniform2f(u.texelSize, texel[0], texel[1]);
        gl.uniform1i(u.uPressure, 0);
        gl.uniform1i(u.uVelocity, 1);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.pressure.read.texture);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
      });
      this.velocity.swap();

      this._setTarget(this.dye.write);
      this._bindSim();
      this._blit(this.p.advect, (u) => {
        gl.uniform2f(u.texelSize, texel[0], texel[1]);
        gl.uniform1f(u.dt, this._simDt);
        gl.uniform1f(u.dissipation, this.dissipationDye);
        gl.uniform1i(u.uVelocity, 0);
        gl.uniform1i(u.uSource, 1);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.velocity.read.texture);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.dye.read.texture);
      });
      this.dye.swap();

      let dyeTex = this.dye.read.texture;
      if (!this.blurFbo) {
        this.blurFbo = this.velocity._fbo(w, h, this.dyeInternal, this.dyeFormat, this.texType, this.linearFilter);
      }
      this._setTarget(this.blurFbo);
      this._bindSim();
      this._blit(this.p.blur, (u) => {
        gl.uniform1i(u.uTexture, 0);
        gl.uniform1f(u.value, 1);
        gl.uniform2f(u.simRes, w, h);
        gl.uniform2f(u.direction, 2, 0);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, dyeTex);
      });
      this._setTarget(this.dye.write);
      this._bindSim();
      this._blit(this.p.blur, (u) => {
        gl.uniform1i(u.uTexture, 0);
        gl.uniform1f(u.value, 1);
        gl.uniform2f(u.simRes, w, h);
        gl.uniform2f(u.direction, 0, 2);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.blurFbo.texture);
      });
      this.dye.swap();
      dyeTex = this.dye.read.texture;

      const magT = tVis * 0.04;
      const wave = Math.sin(magT * 0.55 + Math.PI * 0.5) * 0.5 + 0.5;
      const wave2 = Math.cos(magT * 0.38) * 0.5 + 0.5;
      const raw = wave * 0.55 + wave2 * 0.45;
      const rawMag = raw * raw;
      this._magnetismSmooth += (rawMag - this._magnetismSmooth) * 0.065;
      this._magnetism = this._magnetismSmooth;

      this._renderGradient(tVis);

      this._setTarget(null);
      gl.viewport(0, 0, this.viewW, this.viewH);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      this._bindPreview();
      const prev = this.p.preview;
      gl.useProgram(prev.prog);
      const u = prev.u;
      gl.uniform1f(u.uTime, tVis);
      const circleSize = 1.0;
      const spherePower = this.opts.spherePower != null ? this.opts.spherePower : 1.3;
      const sphereScale = this.opts.sphereScale != null ? this.opts.sphereScale : 1.05;

      gl.uniform1f(u.uCircleSize, circleSize);
      gl.uniform1f(u.uAlpha, 1.0);
      gl.uniform4f(u.uAudioAverage, au.avg[0], au.avg[1], au.avg[2], au.avg[3]);
      gl.uniform4f(u.uAudioAverageInput, au.avgIn[0], au.avgIn[1], au.avgIn[2], au.avgIn[3]);
      gl.uniform4f(u.uCumulativeAudio, au.cum[0], au.cum[1], au.cum[2], au.cum[3]);
      gl.uniform1f(u.uExposure, 0.04);
      gl.uniform1f(u.uContrast, 0.06);
      gl.uniform1f(u.uSaturation, 1.2);
      gl.uniform1f(u.uNoiseOpacity, 0.10);
      gl.uniform1i(u.uNoiseBlendMode, 0);
      // Marketing heroes: near-zero displacement to eliminate deformational jitter
      const isMarketing = this.useStaticAudio;
      gl.uniform1f(u.uAnimatedNoise, isMarketing ? 0.0 : 0.016);
      gl.uniform1f(u.uNoiseSpeed, isMarketing ? 0.004 : 0.018);
      gl.uniform1f(u.uNoiseAmplitude, isMarketing ? 0.0 : 0.016);
      gl.uniform1f(u.uNoiseScale, 2.4);
      gl.uniform1f(u.uSphereScale, sphereScale);
      gl.uniform1f(u.uSpherePower, spherePower);
      gl.uniform3f(u.uFluidColor, this.fluidColor[0], this.fluidColor[1], this.fluidColor[2]);
      gl.uniform1i(u.uFluidBlendMode, 0);
      gl.uniform1f(u.uFluidColorOpacity, isMarketing ? 0.08 : 0.55);
      gl.uniform1f(u.uRingColorOpacity, isMarketing ? 0.0 : 0.12);
      gl.uniform1f(u.uFbmScale, 2.05);
      gl.uniform1f(u.uFbmPower, 1.0);
      gl.uniform1f(u.uFbmAmplitude, isMarketing ? 0.006 : 0.048);
      gl.uniform1f(u.uFbmSpeed, isMarketing ? 0.004 : 0.022);
      gl.uniform1f(u.uFluidDisplace, isMarketing ? 0.003 : 0.022);
      gl.uniform1f(u.uFadeInDuration, 0.0);
      gl.uniform1f(u.uCornerRadius, this.opts.cornerRadius || 6.0);
      gl.uniform2f(u.uResolution, this.viewW, this.viewH);
      gl.uniform1f(u.uDpr, this.dpr);
      gl.uniform2f(u.uTextureResolution, this.texW, this.texH);
      gl.uniform1i(u.uTexture, 0);
      gl.uniform1i(u.uFluidSimTexture, 1);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.gradientFbo.texture);
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, dyeTex);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      gl.disable(gl.BLEND);
      gl.bindVertexArray(null);
    }
  }

  window.LeoFluidGradientPalettes = {
    /** Default Leo Scope hero: Brendan #DA654D + teal + sky / cream (matches homeowners/professionals). */
    brendan: {
      colorA: [...LEO_TERRA_RGB],
      colorB: [...LEO_TEAL_RGB],
      fluidColor: [0.14, 0.4, 0.36],
      gradientColors: {
        a: [...LEO_TERRA_RGB],
        b: [0.96, 0.96, 0.97],
        c: [0.2, 0.19, 0.18],
        d: [0.58, 0.78, 0.88],
        e: [0.94, 0.88, 0.8],
        mid: [...LEO_TERRA_RGB],
        center: [0.65, 0.82, 0.92],
      },
    },
    /**
     * Identical palette to brendan (v4); adds a separate orbiting grass-green blob in-shader
     * (see uGrassWeight / uColorGrass), not blended into d/e/center.
     */
    v5Grass: {
      colorA: [...LEO_TERRA_RGB],
      colorB: [...LEO_TEAL_RGB],
      fluidColor: [0.14, 0.4, 0.36],
      grassColor: [100 / 255, 198 / 255, 92 / 255],
      grassWeight: 1.0,
      gradientColors: {
        a: [...LEO_TERRA_RGB],
        b: [0.88, 0.86, 0.84],
        c: [0.2, 0.19, 0.18],
        d: [0.54, 0.74, 0.85],
        e: [0.9, 0.84, 0.76],
        mid: [...LEO_TERRA_RGB],
        center: [0.58, 0.75, 0.86],
      },
    },
    /**
     * Primarily blue + white; terra only as a soft accent in mid/center + one splat tint.
     * Pair with FluidGradientV6 for a different composition (weaker S-curve, wider lobes).
     */
    blueWhite: {
      colorA: [0.26, 0.46, 0.9],
      colorB: [0.94, 0.84, 0.8],
      fluidColor: [0.15, 0.38, 0.6],
      gradientColors: {
        a: [0.24, 0.44, 0.88],
        b: [0.985, 0.99, 0.996],
        c: [0.74, 0.8, 0.91],
        d: [0.32, 0.5, 0.84],
        e: [0.92, 0.95, 0.99],
        mid: [0.491, 0.544, 0.795],
        center: [0.644, 0.751, 0.894],
      },
    },
    /**
     * Terracotta-first (Brendan #DA654D): warm terra base + highlights; charcoal only
     * for edge structure. Pair with FluidGradientV7 for a distinct orbit/lobe/S layout.
     */
    terraCharcoal: {
      colorA: [...LEO_TERRA_RGB],
      colorB: [0.11, 0.11, 0.12],
      fluidColor: [0.32, 0.17, 0.13],
      gradientColors: {
        a: [...LEO_TERRA_RGB],
        b: [0.88, 0.85, 0.82],
        c: [0.13, 0.12, 0.12],
        d: [0.4, 0.26, 0.22],
        e: [0.92, 0.86, 0.78],
        mid: [...LEO_TERRA_RGB],
        center: [0.94, 0.5, 0.36],
      },
    },
  };

  class FluidGradientV5 extends FluidGradientV4 {
    constructor(canvas, opts) {
      super(canvas, { ...window.LeoFluidGradientPalettes.v5Grass, ...opts });
    }
  }

  class FluidGradientV6 extends FluidGradientV4 {
    constructor(canvas, opts) {
      super(canvas, {
        ...window.LeoFluidGradientPalettes.blueWhite,
        shapeOrbit: 0.64,
        shapeLobe: 1.28,
        shapeWind: 0.68,
        shapeSCurve: 0.2,
        cornerRadius: 28,
        spherePower: 1.64,
        sphereScale: 0.9,
        ...opts,
      });
    }
  }

  class FluidGradientV7 extends FluidGradientV4 {
    constructor(canvas, opts) {
      super(canvas, {
        ...window.LeoFluidGradientPalettes.terraCharcoal,
        pathVariant: 1.0,
        shapeOrbit: 1.2,
        shapeLobe: 0.74,
        shapeWind: 1.08,
        shapeSCurve: 1.38,
        cornerRadius: 14,
        spherePower: 1.2,
        sphereScale: 1.12,
        ...opts,
      });
    }
  }

  window.LeoStoryPalettes = {
    'renovation-disputes-what-to-do': {
      ...window.LeoFluidGradientPalettes.terraCharcoal,
      pathVariant: 0.0, shapeOrbit: 1.4, shapeLobe: 0.9,
      shapeWind: 0.7, shapeSCurve: 1.5,
    },
    'mediation-not-litigation': {
      ...window.LeoFluidGradientPalettes.blueWhite,
      pathVariant: 0.65, shapeOrbit: 0.8, shapeLobe: 1.4,
      shapeWind: 0.5, shapeSCurve: 0.3,
    },
    'escrow-changes-everything': {
      ...window.LeoFluidGradientPalettes.brendan,
      pathVariant: 0.35, shapeOrbit: 1.1, shapeLobe: 0.65,
      shapeWind: 1.2, shapeSCurve: 0.8,
    },
    'managing-expectations-mid-project': {
      colorA: [0.78, 0.42, 0.42], colorB: [0.94, 0.88, 0.80],
      fluidColor: [0.36, 0.22, 0.22],
      gradientColors: {
        a: [0.78, 0.42, 0.42], b: [0.98, 0.96, 0.93],
        c: [0.35, 0.18, 0.18], d: [0.88, 0.72, 0.68],
        e: [0.96, 0.92, 0.88], mid: [0.72, 0.38, 0.38],
        center: [0.94, 0.82, 0.78],
      },
      pathVariant: 0.8, shapeOrbit: 0.6, shapeLobe: 1.3,
      shapeWind: 0.9, shapeSCurve: 1.1,
    },
    'variation-orders-budget-killer': {
      colorA: [0.88, 0.62, 0.24], colorB: [0.18, 0.2, 0.24],
      fluidColor: [0.4, 0.28, 0.12],
      gradientColors: {
        a: [0.88, 0.62, 0.24], b: [0.96, 0.92, 0.82],
        c: [0.18, 0.2, 0.24], d: [0.52, 0.38, 0.18],
        e: [0.94, 0.88, 0.76], mid: [0.82, 0.56, 0.2],
        center: [0.72, 0.58, 0.36],
      },
      pathVariant: 0.45, shapeOrbit: 1.6, shapeLobe: 0.55,
      shapeWind: 1.4, shapeSCurve: 0.5,
    },
    'hiring-contractor-trust-checklist': {
      colorA: [0.16, 0.42, 0.28], colorB: [0.92, 0.86, 0.76],
      fluidColor: [0.12, 0.3, 0.2],
      gradientColors: {
        a: [0.16, 0.42, 0.28], b: [0.96, 0.94, 0.9],
        c: [0.1, 0.2, 0.14], d: [0.38, 0.56, 0.44],
        e: [0.92, 0.88, 0.8], mid: [0.22, 0.48, 0.34],
        center: [0.68, 0.78, 0.7],
      },
      pathVariant: 1.0, shapeOrbit: 0.9, shapeLobe: 1.15,
      shapeWind: 0.6, shapeSCurve: 1.35,
    },
    'how-to-write-winning-quotes': {
      ...window.LeoFluidGradientPalettes.terraCharcoal,
      pathVariant: 0.7, shapeOrbit: 0.7, shapeLobe: 1.5,
      shapeWind: 1.1, shapeSCurve: 0.6,
    },
    'best-quoting-tools-contractors-2026': {
      colorA: [0.85, 0.4, 0.3], colorB: [0.28, 0.32, 0.42],
      fluidColor: [0.24, 0.22, 0.3],
      gradientColors: {
        a: [0.85, 0.4, 0.3], b: [0.92, 0.9, 0.88],
        c: [0.22, 0.24, 0.32], d: [0.45, 0.48, 0.58],
        e: [0.88, 0.84, 0.8], mid: [0.68, 0.36, 0.28],
        center: [0.58, 0.56, 0.62],
      },
      pathVariant: 0.2, shapeOrbit: 1.3, shapeLobe: 0.8,
      shapeWind: 0.85, shapeSCurve: 1.6,
    },
    'can-ai-mediate-renovation-dispute': {
      colorA: [0.32, 0.38, 0.82], colorB: [0.88, 0.78, 0.92],
      fluidColor: [0.18, 0.2, 0.52],
      gradientColors: {
        a: [0.32, 0.38, 0.82], b: [0.94, 0.92, 0.96],
        c: [0.12, 0.12, 0.28], d: [0.22, 0.26, 0.58],
        e: [0.86, 0.84, 0.92], mid: [0.4, 0.36, 0.72],
        center: [0.62, 0.6, 0.82],
      },
      pathVariant: 0.55, shapeOrbit: 1.0, shapeLobe: 1.0,
      shapeWind: 1.3, shapeSCurve: 0.9,
    },
  };

  function initGradients() {
    const brendan = window.LeoFluidGradientPalettes.brendan;
    document.querySelectorAll('.fluid-gradient').forEach((el) => {
      const canvas = el.querySelector('canvas');
      if (canvas && !canvas._fluidGradient) {
        canvas._fluidGradient = new FluidGradientV4(canvas, {
          ...brendan,
          colorA: [16 / 255, 185 / 255, 129 / 255],
          colorB: [...LEO_TERRA_RGB],
        });
      }
    });
    /** Landing heroes: every `.hero-box.hero-fluid-live` gets its own canvas (top + bottom CTA). */
    const heroCanvases = document.querySelectorAll('.hero-box.hero-fluid-live > canvas.el-gradient__canvas');
    heroCanvases.forEach((heroCanvas) => {
      if (heroCanvas.getAttribute('data-leo-fluid-skip') === '1') {
        return;
      }
      if (heroCanvas._fluidGradient) {
        return;
      }
      const raw = (heroCanvas.getAttribute('data-leo-fluid') || 'v4').trim().toLowerCase();
      const ver = raw.replace(/^fluid\s*gradient\s*/i, '').replace(/\s+/g, '');
      let Ctor = FluidGradientV4;
      if (ver === 'v5' || ver === '5') Ctor = FluidGradientV5;
      else if (ver === 'v6' || ver === '6') Ctor = FluidGradientV6;
      else if (ver === 'v7' || ver === '7') Ctor = FluidGradientV7;
      let fpsCap = 24;
      const rawFps = heroCanvas.getAttribute('data-leo-fluid-fps');
      if (rawFps) {
        const p = parseFloat(rawFps, 10);
        if (Number.isFinite(p) && p > 0 && p <= 60) fpsCap = p;
      }
      heroCanvas._fluidGradient = new Ctor(heroCanvas, {
        fpsCap,
        useStaticAudio: true,
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGradients);
  } else {
    setTimeout(initGradients, 0);
  }

  window.FluidGradientV4 = FluidGradientV4;
  window.FluidGradientV5 = FluidGradientV5;
  window.FluidGradientV6 = FluidGradientV6;
  window.FluidGradientV7 = FluidGradientV7;
})();
