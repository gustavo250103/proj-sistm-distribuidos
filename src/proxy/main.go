package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"  // captura Ctrl+C
	"syscall"
	"time"

	zmq "github.com/go-zeromq/zmq4" // implementação pure Go do ZeroMQ
)

// endereços padrão usados no projeto
var (
	xsubAddr = getenv("XSUB_ADDR", "tcp://*:5557") // onde o servidor.PUB conecta
	xpubAddr = getenv("XPUB_ADDR", "tcp://*:5558") // onde os clientes.SUB conectam
)

// pega variável de ambiente ou usa default
func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func main() {
	ctx, cancel := context.WithCancel(context.Background()) // contexto para parar tudo
	defer cancel()

	// trata Ctrl+C para desligar bonitinho
	sigc := make(chan os.Signal, 1)
	signal.Notify(sigc, os.Interrupt, syscall.SIGTERM)
	go func() { <-sigc; cancel() }()

	// socket XSUB recebe publicações do servidor
	xsub := zmq.NewXSUB(ctx)
	defer xsub.Close()

	// socket XPUB envia para os assinantes (clientes)
	xpub := zmq.NewXPUB(ctx)
	defer xpub.Close()

	// abre as portas para os dois lados
	if err := xsub.Listen(xsubAddr); err != nil {
		log.Fatalf("XSUB bind error: %v", err)
	}
	if err := xpub.Listen(xpubAddr); err != nil {
		log.Fatalf("XPUB bind error: %v", err)
	}
	fmt.Printf("[proxy-go] XSUB on %s | XPUB on %s\n", xsubAddr, xpubAddr)

	// canal para reportar erro na bomba de publicações
	pubErr := make(chan error, 1)
	go func() {
		for {
			msg, err := xsub.Recv() // recebe mensagem (pode ser multipart)
			if err != nil {
				pubErr <- err        // manda erro e encerra
				return
			}
			if err := xpub.Send(msg); err != nil { // repassa aos subscribers
				pubErr <- err
				return
			}
		}
	}()

	// canal para reportar erro nas assinaturas
	subErr := make(chan error, 1)
	go func() {
		for {
			msg, err := xpub.Recv() // comandos de subscribe/unsubscribe dos clientes
			if err != nil {
				subErr <- err
				return
			}
			if err := xsub.Send(msg); err != nil { // repassa pro lado dos publishers
				subErr <- err
				return
			}
		}
	}()

	// fica esperando cancelamento ou erro
	select {
	case <-ctx.Done():                                  // usuário mandou parar
		fmt.Println("[proxy-go] shutting down...")
	case err := <-pubErr:                               // erro na bomba de publicações
		log.Fatalf("[proxy-go] publish pump error: %v", err)
	case err := <-subErr:                               // erro na bomba de assinaturas
		log.Fatalf("[proxy-go] subscribe pump error: %v", err)
	}

	time.Sleep(200 * time.Millisecond) // pequeno delay para flush antes de sair
}
