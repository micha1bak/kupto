import { SignJWT, jwtVerify } from 'jose';
import { cookies } from 'next/headers';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

export async function signJWT(payload: { userId: number }) {
  return await new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('30d')
    .sign(secret);
}

export async function verifyJWT(token: string) {
  try {
    const { payload } = await jwtVerify(token, secret);
    return payload as { userId: number };
  } catch (err) {
    return null;
  }
}

export async function getSession() {
  const token = (await cookies()).get('token')?.value;
  if (!token) return null;
  return await verifyJWT(token);
}
