/**
 * Visualizador Sináptico 3D para DragonBRX
 * Renderiza uma representação visual 3D dinâmica da consciência usando Three.js
 * 
 * Uso:
 * const visualizer = new SynapticVisualizer();
 * visualizer.init();
 * visualizer.updateAffectiveState({ valence: 0.5, arousal: 0.3, dominance: 0.6 });
 * visualizer.animate();
 */

class SynapticVisualizer {
    constructor(containerId = "dragonbrx-container") {
        this.containerId = containerId;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.synapticNetwork = null;
        this.affectiveState = { valence: 0.0, arousal: 0.0, dominance: 0.5 };
        this.neurons = [];
        this.synapses = [];
        this.coreEnergy = null;
        this.animationId = null;
        this.time = 0;
    }

    init() {
        // Obtém o container
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`Container with ID '${this.containerId}' not found.`);
            return;
        }

        // Configurar cena
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0e27); // Fundo escuro

        // Configurar câmera
        const width = container.clientWidth;
        const height = container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        this.camera.position.z = 30;

        // Configurar renderizador
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(this.renderer.domElement);

        // Adicionar iluminação
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x00ff88, 1, 100);
        pointLight.position.set(20, 20, 20);
        this.scene.add(pointLight);

        // Criar rede sináptica
        this._createSynapticNetwork();

        // Criar núcleo de energia central
        this._createCoreEnergy();

        // Ajustar tamanho ao redimensionar a janela
        window.addEventListener("resize", () => this._onWindowResize());

        console.log("SynapticVisualizer initialized.");
    }

    _createSynapticNetwork() {
        this.synapticNetwork = new THREE.Group();
        this.scene.add(this.synapticNetwork);

        // Número de neurônios
        const neuronCount = 50;

        // Criar neurônios (pontos de luz)
        for (let i = 0; i < neuronCount; i++) {
            const geometry = new THREE.SphereGeometry(0.3, 8, 8);
            const material = new THREE.MeshBasicMaterial({ color: 0x00ff88 });
            const neuron = new THREE.Mesh(geometry, material);

            // Posicionar aleatoriamente em uma esfera
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI;
            const radius = 15 + Math.random() * 5;

            neuron.position.set(
                radius * Math.sin(phi) * Math.cos(theta),
                radius * Math.sin(phi) * Math.sin(theta),
                radius * Math.cos(phi)
            );

            neuron.originalPosition = neuron.position.clone();
            neuron.pulsePhase = Math.random() * Math.PI * 2;

            this.synapticNetwork.add(neuron);
            this.neurons.push(neuron);
        }

        // Criar sinapses (linhas conectoras)
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x00ff88, linewidth: 1, transparent: true, opacity: 0.3 });
        
        for (let i = 0; i < neuronCount; i++) {
            // Conectar cada neurônio a 2-3 neurônios aleatórios
            const connectionCount = 2 + Math.floor(Math.random() * 2);
            for (let j = 0; j < connectionCount; j++) {
                const targetIndex = Math.floor(Math.random() * neuronCount);
                if (targetIndex !== i) {
                    const points = [this.neurons[i].position, this.neurons[targetIndex].position];
                    const geometry = new THREE.BufferGeometry().setFromPoints(points);
                    const line = new THREE.Line(geometry, lineMaterial);
                    this.synapticNetwork.add(line);
                    this.synapses.push({ line, from: i, to: targetIndex });
                }
            }
        }

        console.log(`Created ${neuronCount} neurons and ${this.synapses.length} synapses.`);
    }

    _createCoreEnergy() {
        // Núcleo central que representa a "essência" do DragonBRX
        const coreGeometry = new THREE.IcosahedronGeometry(2, 4);
        const coreMaterial = new THREE.MeshPhongMaterial({
            color: 0xff00ff,
            emissive: 0xff00ff,
            shininess: 100,
            wireframe: false
        });
        this.coreEnergy = new THREE.Mesh(coreGeometry, coreMaterial);
        this.coreEnergy.position.set(0, 0, 0);
        this.scene.add(this.coreEnergy);

        // Adicionar uma aura ao redor do núcleo
        const auraGeometry = new THREE.IcosahedronGeometry(3, 3);
        const auraMaterial = new THREE.MeshBasicMaterial({
            color: 0xff00ff,
            transparent: true,
            opacity: 0.2,
            wireframe: true
        });
        const aura = new THREE.Mesh(auraGeometry, auraMaterial);
        this.scene.add(aura);
        this.aura = aura;
    }

    updateAffectiveState(affectiveState) {
        this.affectiveState = { ...this.affectiveState, ...affectiveState };
        console.log(`Updated affective state: ${JSON.stringify(this.affectiveState)}`);
    }

    _updateVisualization() {
        this.time += 0.01;

        // Atualizar cor da rede sináptica baseado em valência
        const valence = this.affectiveState.valence; // -1 (vermelho) a 1 (verde)
        const hue = (valence + 1) / 2; // Mapear para 0-1
        const color = new THREE.Color().setHSL(hue * 0.3, 1, 0.5); // Verde a Vermelho

        this.neurons.forEach((neuron, index) => {
            // Pulsação dos neurônios
            const pulse = 0.3 + 0.2 * Math.sin(this.time + neuron.pulsePhase);
            neuron.material.color.copy(color);
            neuron.scale.set(pulse, pulse, pulse);

            // Movimento suave baseado em arousal
            const arousal = this.affectiveState.arousal;
            const movementAmount = arousal * 0.5;
            const angle = this.time * arousal + index;
            neuron.position.x = neuron.originalPosition.x + Math.sin(angle) * movementAmount;
            neuron.position.y = neuron.originalPosition.y + Math.cos(angle) * movementAmount;
            neuron.position.z = neuron.originalPosition.z + Math.sin(angle * 0.5) * movementAmount;
        });

        // Atualizar sinapses
        this.synapses.forEach((synapse) => {
            const fromPos = this.neurons[synapse.from].position;
            const toPos = this.neurons[synapse.to].position;
            const points = [fromPos, toPos];
            synapse.line.geometry.setFromPoints(points);

            // Opacidade baseada em arousal
            synapse.line.material.opacity = 0.1 + this.affectiveState.arousal * 0.3;
        });

        // Atualizar núcleo de energia
        if (this.coreEnergy) {
            this.coreEnergy.rotation.x += 0.005;
            this.coreEnergy.rotation.y += 0.01;
            this.coreEnergy.rotation.z += 0.007;

            // Escala do núcleo baseada em dominância
            const dominance = this.affectiveState.dominance;
            const coreScale = 1 + dominance * 0.5;
            this.coreEnergy.scale.set(coreScale, coreScale, coreScale);

            // Intensidade de emissão baseada em arousal
            const emissiveIntensity = 0.5 + this.affectiveState.arousal * 0.5;
            this.coreEnergy.material.emissiveIntensity = emissiveIntensity;
        }

        // Atualizar aura
        if (this.aura) {
            this.aura.rotation.x -= 0.003;
            this.aura.rotation.y -= 0.005;
            const auraScale = 1.5 + Math.sin(this.time) * 0.3;
            this.aura.scale.set(auraScale, auraScale, auraScale);
            this.aura.material.opacity = 0.1 + this.affectiveState.arousal * 0.2;
        }

        // Rotacionar toda a rede
        if (this.synapticNetwork) {
            this.synapticNetwork.rotation.x += 0.0002;
            this.synapticNetwork.rotation.y += 0.0005;
        }
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        this._updateVisualization();
        this.renderer.render(this.scene, this.camera);
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    _onWindowResize() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const width = container.clientWidth;
        const height = container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    dispose() {
        this.stop();
        const container = document.getElementById(this.containerId);
        if (container && this.renderer.domElement.parentNode === container) {
            container.removeChild(this.renderer.domElement);
        }
        this.renderer.dispose();
    }
}

// Exportar para uso em Node.js (se necessário)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SynapticVisualizer;
}
