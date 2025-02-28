import { PublicKey, Transaction } from '@solana/web3.js';
import { WalletAdapterNetwork } from '@solana/wallet-adapter-base';
import * as bs58 from 'bs58';
import axios from 'axios';

export interface PhantomProvider {
    connect: (params?: { onlyIfTrusted?: boolean }) => Promise<{ publicKey: PublicKey }>;
    disconnect: () => Promise<void>;
    signMessage: (message: Uint8Array) => Promise<{ signature: Uint8Array }>;
    signTransaction: (transaction: Transaction) => Promise<Transaction>;
    signAllTransactions: (transactions: Transaction[]) => Promise<Transaction[]>;
    isConnected: boolean;
    publicKey: PublicKey | null;
    isPhantom?: boolean;
}

declare global {
    interface Window {
        solana?: PhantomProvider;
    }
}

export class PhantomWalletService {
    private apiClient = axios.create({
        baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001/api',
        withCredentials: true
    });

    // Utility method to check if Phantom wallet is installed
    public isPhantomInstalled(): boolean {
        return typeof window !== 'undefined' && 
               'solana' in window && 
               !!(window.solana?.isPhantom);
    }

    // Utility method to get the Phantom provider
    public getPhantomProvider(): PhantomProvider | null {
        return this.isPhantomInstalled() ? window.solana || null : null;
    }

    // Utility method to get network configuration
    public getNetworkConfig(): WalletAdapterNetwork {
        // You can expand this to dynamically select network based on environment
        return WalletAdapterNetwork.Mainnet;
    }

    // Utility method to get RPC URL
    public getRpcUrl(): string {
        return import.meta.env.VITE_SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';
    }

    // Async utility method to verify wallet signature
    public async verifySignature(
        publicKey: PublicKey, 
        message: string, 
        signature: Uint8Array
    ): Promise<boolean> {
        try {
            const response = await this.apiClient.post('/soleco/wallet/verify-signature', {
                public_key: publicKey.toBase58(),
                message: bs58.encode(Buffer.from(message)),
                signature: bs58.encode(signature)
            });

            return response.data.valid === true;
        } catch (error) {
            console.error('Signature verification failed', error);
            return false;
        }
    }

    // Async utility method to get wallet balance
    public async getWalletBalance(publicKey: PublicKey): Promise<number> {
        try {
            const response = await this.apiClient.get(`/soleco/wallet/balance/${publicKey.toBase58()}`);
            return response.data.balance;
        } catch (error) {
            console.error('Failed to fetch wallet balance', error);
            return 0;
        }
    }

    // Utility method to import a wallet via private key
    public async importWallet(privateKey: string): Promise<PublicKey | null> {
        try {
            const response = await this.apiClient.post('/soleco/wallet/import', { 
                private_key: privateKey 
            });
            
            return response.data.public_key 
                ? new PublicKey(response.data.public_key) 
                : null;
        } catch (error) {
            console.error('Wallet import failed', error);
            return null;
        }
    }
}

// Singleton instance for easy access
export const phantomWallet = new PhantomWalletService();