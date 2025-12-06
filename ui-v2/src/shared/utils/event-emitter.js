/**
 * Simple Event Emitter Implementation
 * ===================================
 * 
 * Lightweight event system for WebSocket and other services
 */

export class EventEmitter {
    constructor() {
        this.events = new Map();
    }
    
    on(eventName, listener) {
        /**
         * Add event listener
         */
        if (!this.events.has(eventName)) {
            this.events.set(eventName, []);
        }
        
        this.events.get(eventName).push(listener);
        
        // Return unsubscribe function
        return () => this.off(eventName, listener);
    }
    
    once(eventName, listener) {
        /**
         * Add event listener that runs only once
         */
        const wrapper = (...args) => {
            listener(...args);
            this.off(eventName, wrapper);
        };
        
        return this.on(eventName, wrapper);
    }
    
    off(eventName, listener) {
        /**
         * Remove event listener
         */
        if (!this.events.has(eventName)) {
            return false;
        }
        
        const listeners = this.events.get(eventName);
        const index = listeners.indexOf(listener);
        
        if (index > -1) {
            listeners.splice(index, 1);
            
            // Clean up empty arrays
            if (listeners.length === 0) {
                this.events.delete(eventName);
            }
            
            return true;
        }
        
        return false;
    }
    
    emit(eventName, ...args) {
        /**
         * Emit event to all listeners
         */
        if (!this.events.has(eventName)) {
            return false;
        }
        
        const listeners = this.events.get(eventName).slice(); // Copy to avoid modification during iteration
        
        listeners.forEach(listener => {
            try {
                listener(...args);
            } catch (error) {
                console.error(`Error in event listener for "${eventName}":`, error);
            }
        });
        
        return true;
    }
    
    removeAllListeners(eventName) {
        /**
         * Remove all listeners for an event
         */
        if (eventName) {
            this.events.delete(eventName);
        } else {
            this.events.clear();
        }
    }
    
    listenerCount(eventName) {
        /**
         * Get number of listeners for an event
         */
        return this.events.has(eventName) ? this.events.get(eventName).length : 0;
    }
    
    eventNames() {
        /**
         * Get all event names
         */
        return Array.from(this.events.keys());
    }
}